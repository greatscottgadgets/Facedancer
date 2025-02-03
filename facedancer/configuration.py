#
# This file is part of Facedancer.
#
""" Functionality for describing USB device configurations. """

import struct
import textwrap

from dataclasses  import field
from typing       import Iterable

from .types       import USBDirection
from .magic       import instantiate_subordinates, AutoInstantiable
from .request     import USBRequestHandler

from .interface   import USBInterface
from .descriptor  import USBDescribable, USBDescriptor, StringRef
from .endpoint    import USBEndpoint


class USBConfiguration(USBDescribable, AutoInstantiable, USBRequestHandler):
    """ Class representing a USBDevice's configuration.

    Fields:
        number:
            The configuration's number; one-indexed.
        configuration_string
            A string describing the configuration; or None if not provided.
        max_power:
            The maximum power expected to be drawn by the device when using this interface, in mA. Typically 500mA, for maximum possible.
        supports_remote_wakeup:
            True iff this device should be able to wake the host from suspend.
    """

    DESCRIPTOR_TYPE_NUMBER  = 0x02
    DESCRIPTOR_SIZE_BYTES   = 9

    number                 : int            = 1
    configuration_string   : StringRef      = None

    max_power              : int            = 500

    self_powered           : bool           = True
    supports_remote_wakeup : bool           = True

    parent                 : USBDescribable = None
    interfaces             : USBInterface   = field(default_factory=dict)


    @classmethod
    def from_binary_descriptor(cls, data, strings={}):
        """
        Generates a new USBConfiguration object from a configuration descriptor,
        handling any attached subordinate descriptors.

        Args:
            data: The raw bytes for the descriptor to be parsed.
        """

        length = data[0]

        # Unpack the main collection of data into the descriptor itself.
        descriptor_type, total_length, num_interfaces, index, string_index, \
            attributes, half_max_power = struct.unpack_from('<xBHBBBBB', data[0:length])

        configuration = cls(
            number=index,
            configuration_string=StringRef.lookup(strings, string_index),
            max_power=half_max_power * 2,
            self_powered=bool((attributes >> 6) & 1),
            supports_remote_wakeup=bool((attributes >> 5) & 1),
        )

        data = data[length:total_length]
        last_interface = None
        last_endpoint  = None

        # Continue parsing until we run out of descriptors.
        while data:

            # Determine the length and type of the next descriptor.
            length     = data[0]
            descriptor = USBDescribable.from_binary_descriptor(data[:length], strings=strings)

            # If we have an interface descriptor, add it to our list of interfaces.
            if isinstance(descriptor, USBInterface):
                configuration.add_interface(descriptor)
                last_interface = descriptor
                last_endpoint = None
            elif isinstance(descriptor, USBEndpoint):
                last_interface.add_endpoint(descriptor)
                last_endpoint = descriptor
            elif isinstance(descriptor, USBDescriptor):
                descriptor.include_in_config = True
                if len(last_interface.endpoints) == 0:
                    last_interface.add_descriptor(descriptor)
                else:
                    last_endpoint.add_descriptor(descriptor)

            # Move on to the next descriptor.
            data = data[length:]

        return configuration


    def __post_init__(self):

        self.configuration_string = StringRef.ensure(self.configuration_string)

        # Gather any interfaces attached to the configuration.
        for interface in instantiate_subordinates(self, USBInterface):
            self.add_interface(interface)


    @property
    def attributes(self):
        """ Retrives the "attributes" composite word. """

        # Start off with the required bits set to one...
        attributes = 0b10000000

        # ... and then add in our attributes.
        attributes |= (1 << 6) if self.self_powered           else 0
        attributes |= (1 << 5) if self.supports_remote_wakeup else 0


        return attributes

    #
    # User API.
    #

    def get_device(self):
        """ Returns a reference to the associated device."""
        return self.parent


    def add_interface(self, interface: USBInterface):
        """ Adds an interface to the configuration. """
        identifier = interface.get_identifier()
        num, alt = identifier

        if identifier in self.interfaces:
            other = self.interfaces[identifier]
            iface_name = type(interface).__name__
            other_name = type(other).__name__
            raise Exception(
                f"Interface of type {iface_name} cannot be added to this "
                f"configuration because there is already an interface of "
                f"type {other_name} with the same interface number {num} "
                f"and alternate setting {alt}")
        else:
            self.interfaces[identifier] = interface
            interface.parent = self


    def get_endpoint(self, number: int, direction: USBDirection) -> USBEndpoint:
        """ Attempts to find an endpoint with the given number + direction.

        Args:
            number    : The endpoint number to look for.
            direction : Whether to look for an IN or OUT endpoint.
        """

        # Search each of our interfaces for the relevant endpoint.
        if hasattr(self, 'active_interfaces'):
            for interface in self.active_interfaces.values():
                endpoint = interface.get_endpoint(number, direction)
                if endpoint is not None:
                    return endpoint

        # If none have one, return None.
        return None


    #
    # Event handlers.
    #


    def handle_data_received(self, endpoint: USBEndpoint, data: bytes):
        """ Handler for receipt of non-control request data.

        Typically, this method will delegate any data received to the
        appropriate configuration/interface/endpoint. If overridden, the
        overriding function will receive all data; and can delegate it by
        calling the `.handle_data_received` method on `self.configuration`.

        Args:
            endpoint : The endpoint on which the data was received.
            data     : The raw bytes received on the relevant endpoint.
        """

        if hasattr(self, 'active_interfaces'):
            for interface in self.active_interfaces.values():
                if interface.has_endpoint(endpoint.number, direction=USBDirection.OUT):
                    interface.handle_data_received(endpoint, data)
                    return

        # If no interface owned the targeted endpoint, consider the data unexpected.
        self.get_device().handle_unexpected_data_received(endpoint.number, data)


    def handle_data_requested(self, endpoint: USBEndpoint):
        """ Handler called when the host requests data on a non-control endpoint.

        Typically, this method will delegate the request to the appropriate
        interface+endpoint. If overridden, the overriding function will receive
        all data.

        Args:
            endpoint : The endpoint on which the host requested data.
        """

        if hasattr(self, 'active_interfaces'):
            for interface in self.active_interfaces.values():
                if interface.has_endpoint(endpoint.number, direction=USBDirection.IN):
                    interface.handle_data_requested(endpoint)
                    return

        # If no one interface owned the targeted endpoint, consider the data unexpected.
        self.get_device().handle_unexpected_data_requested(endpoint.number)


    def handle_buffer_empty(self, endpoint: USBEndpoint):
        """ Handler called when a given endpoint first has an empty buffer.

        Often, an empty buffer indicates an opportunity to queue data
        for sending ('prime an endpoint'), but doesn't necessarily mean
        that the host is planning on reading the data.

        This function is called only once per buffer.
        """

        if hasattr(self, 'active_interfaces'):
            for interface in self.active_interfaces.values():
                if interface.has_endpoint(endpoint.number, direction=USBDirection.IN):
                    interface.handle_buffer_empty(endpoint)
                    return



    #
    # Backend interface functions.
    #

    def get_interfaces(self) -> Iterable[USBInterface]:
        """ Returns an iterable over all interfaces on the provided device. """
        return self.interfaces.values()


    def get_descriptor(self) -> bytes:
        """ Returns this configuration's configuration descriptor, including subordinates. """
        interface_descriptors = bytearray()

        # FIXME: use construct

        # All all subordinate descriptors together to create a big subordinate descriptor.
        for interface in self.interfaces.values():
            interface_descriptors += interface.get_descriptor()

        total_len      = len(interface_descriptors) + 9
        string_manager = self.get_device().strings

        # Build the core interface descriptor.
        d = bytes([
                9,          # length of descriptor in bytes
                2,          # descriptor type 2 == configuration
                total_len & 0xff,
                (total_len >> 8) & 0xff,
                len(set(interface.number for interface in self.interfaces.values())),
                self.number,
                string_manager.get_index(self.configuration_string),
                self.attributes,
                self.max_power // 2
        ])

        return d + interface_descriptors


    #
    # Interfacing functions for AutoInstantiable.
    #
    def get_identifier(self) -> int:
        return self.number


    #
    # Backend functions for our RequestHandler class.
    #

    def _request_handlers(self) -> Iterable[callable]:
        return ()

    def _get_subordinate_handlers(self) -> Iterable[USBInterface]:
        return self.interfaces.values()


    def generate_code(self, name=None, indent=0):

        if name is None:
            name = f"Configuration_{self.number}"

        code = f"""
class {name}(USBConfiguration):
    number                 = {self.number}
    configuration_string   = {self.configuration_string.generate_code()}
    max_power              = {self.max_power}
    self_powered           = {repr(self.self_powered)}
    supports_remote_wakeup = {repr(self.supports_remote_wakeup)}
"""

        for interface in self.interfaces.values():
            code += interface.generate_code(indent=4)

        return textwrap.indent(code, indent * ' ')
