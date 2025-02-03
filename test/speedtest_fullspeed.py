#!/usr/bin/env python3
#
#
"""
USB full-speed speedtest
"""

from facedancer.devices import default_main
from facedancer import *


@use_inner_classes_automatically
class USBSpeedtest(USBDevice):
    """Loopback on EP1"""

    name: str = "USB full-speed speedtest"
    product_string: str = "USB full-speed speedtest"
    max_packet_size_ep0: int = 64
    device_speed : DeviceSpeed = DeviceSpeed.FULL

    EP_MAX_SIZE = 64
    buffer = [None, None, None, None, None]
    random_buffer = [i % 256 for i in range(64)]

    class USBSpeedtestConfiguration(USBConfiguration):
        """USB full-speed speedtest"""

        max_power: int = 100
        self_powered: bool = False
        supports_remote_wakeup: bool = True

        class USBSpeedtestInterface(USBInterface):
            """Core interface"""

            name: str = "USB full-speed speedtest"
            class_number: int = 0xff  # Vendor class

            class USBSpeedtestOUT(USBEndpoint):
                """Interrupt OUT endpoint"""

                number: int = 1
                direction: USBDirection = USBDirection.OUT
                transfer_type: USBTransferType = USBTransferType.BULK
                max_packet_size: int = 64

            class USBSpeedtestIN(USBEndpoint):
                """Interrupt IN endpoint"""

                number: int = 2
                direction: USBDirection = USBDirection.IN
                transfer_type: USBTransferType = USBTransferType.BULK
                max_packet_size: int = 64

    @class_request_handler(number=USBStandardRequests.GET_INTERFACE)
    @to_this_interface
    def handle_get_interface_request(self, request):
        # Silently stall GET_INTERFACE class requests.
        request.stall()

    def handle_data_received(self, ep, data):
        print(f"received {len(data)} bytes on {ep}")
        self.buffer[ep.number] = data

    def handle_data_requested(self, ep):
        """Provide data once per host request."""
        print(f"sending {len(self.random_buffer)} bytes on {ep}")
        self.send(ep.number, self.random_buffer)

    def handle_buffer_empty(self, endpoint: USBEndpoint):
        """ Handler called when a given endpoint first has an empty buffer.

        Often, an empty buffer indicates an opportunity to queue data
        for sending ('prime an endpoint'), but doesn't necessarily mean
        that the host is planning on reading the data.

        This function is called only once per buffer.
        """
        print(f"priming {len(self.random_buffer)} bytes on {endpoint}")
        self.send(endpoint.number, self.random_buffer)


if __name__ == "__main__":
    default_main(USBSpeedtest)
