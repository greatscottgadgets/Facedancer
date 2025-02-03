#!/usr/bin/env python3

from facedancer import main
from facedancer import *
from facedancer.classes import USBDeviceClass
import logging
import time
import datetime


class EndOfEnumerationException(Exception):
    pass


@use_inner_classes_automatically
class SomeDevice(USBDevice):
    """ Emulate a USB Device"""

    device_class: int = 0
    device_subclass: int = 0
    protocol_revision_number: int = 0

    max_packet_size_ep0: int = 64
    vendor_id: int = 0x610b
    product_id: int = 0x4653
    manufacturer_string: str = "FaceDancer"
    product_string: str = "Generic USB Device"
    serial_number_string: str = "S/N 3420E"
    supported_languages: tuple = (LanguageIDs.ENGLISH_US,)
    device_revision: int = 0
    usb_spec_version: int = 0x0002
    device_speed : DeviceSpeed = DeviceSpeed.FULL

    class SomeConfiguration(USBConfiguration):
        configuration_number: int = 1
        configuration_string: str = None
        self_powered: bool = False
        supports_remote_wakeup: bool = True
        max_power: int = 500

        class SomeTemplate(USBInterface):
            number: int = 0
            class_number: int = USBDeviceClass.VENDOR_SPECIFIC
            subclass_number: int = 0
            protocol_number: int = 0
            interface_string: str = None

            class INEndpoint(USBEndpoint):
                number: int = 1
                direction: USBDirection = USBDirection.IN
                transfer_type: USBTransferType = USBTransferType.BULK
                max_packet_size: int = 64
                interval: int = 0

                def handle_data_requested(self):
                    self.send(b"Hello!")

            class OUTEndpoint(USBEndpoint):
                number: int = 1
                direction: USBDirection = USBDirection.OUT
                transfer_type: USBTransferType = USBTransferType.BULK
                max_packet_size: int = 64
                interval: int = 0

                def handle_data_received(self, data):
                    logging.info(f"Received data: {data}")

    def handle_data_received(self, endpoint, data):
        super().handle_data_received(endpoint, data)

    @standard_request_handler(number=USBStandardRequests.SET_CONFIGURATION)
    @to_device
    def handle_set_configuration_request(self, request):
        """ Handle SET_CONFIGURATION requests; per USB2 [9.4.7] """
        print("received SET_CONFIGURATION request")

        # If the host is requesting configuration zero, they're asking
        # us to drop our configuration.
        if request.value == 0:
            self.configuration = None
            request.acknowledge()

        # Otherwise, we'll find a given configuration and apply it.
        else:
            try:
                self.configuration = self.configurations[request.value]
                request.acknowledge()
            except KeyError:
                request.stall()

        # Notify the backend of the reconfiguration, in case
        # it needs to e.g. set up endpoints accordingly
        self.backend.configured(self.configuration)
        raise EndOfEnumerationException()


if __name__ == "__main__":

    count = 1000

    START = datetime.datetime.now()
    for i in range(count):
        print("Start of enumeration")
        try:
            main(SomeDevice)
        except EndOfEnumerationException:
            print("End of enumeration")
    STOP = datetime.datetime.now()

    print(f"Success, enumerated {count} devices, took {STOP-START}")
