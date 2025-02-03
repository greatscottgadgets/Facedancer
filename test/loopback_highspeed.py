#!/usr/bin/env python3
#
#
"""
Create a basic mouse device with three buttons and two axis
"""

from facedancer.devices import default_main
from facedancer import *


@use_inner_classes_automatically
class USBLoopback(USBDevice):
    """Loopback on EP1"""

    name: str = "USB EP1 Loopback"
    product_string: str = "Loopback device"
    max_packet_size_ep0: int = 64
    device_speed : DeviceSpeed = DeviceSpeed.HIGH

    EP_MAX_SIZE = 512
    buffer = [None, None, None, None, None]

    class USBLoopbackConfiguration(USBConfiguration):
        """Primary configuration : act as a mouse"""

        max_power: int = 100
        self_powered: bool = False
        supports_remote_wakeup: bool = True
        ep_in_ready: bool = False

        class USBLoopbackInterface(USBInterface):
            """Core interface"""

            name: str = "Loopback device"
            class_number: int = 0xff  # Vendor class

            class USBLoopbackOUT1(USBEndpoint):
                """Interrupt IN endpoint for guaranteed max latency"""

                number: int = 1
                direction: USBDirection = USBDirection.OUT
                transfer_type: USBTransferType = USBTransferType.BULK
                max_packet_size: int = 512

            class USBLoopbackIN1(USBEndpoint):
                """Interrupt IN endpoint for guaranteed max latency"""

                number: int = 1
                direction: USBDirection = USBDirection.IN
                transfer_type: USBTransferType = USBTransferType.BULK
                max_packet_size: int = 512

            class USBLoopbackOUT2(USBEndpoint):
                """Interrupt IN endpoint for guaranteed max latency"""

                number: int = 2
                direction: USBDirection = USBDirection.OUT
                transfer_type: USBTransferType = USBTransferType.BULK
                max_packet_size: int = 512

            class USBLoopbackIN2(USBEndpoint):
                """Interrupt IN endpoint for guaranteed max latency"""

                number: int = 2
                direction: USBDirection = USBDirection.IN
                transfer_type: USBTransferType = USBTransferType.BULK
                max_packet_size: int = 512

            class USBLoopbackOUT3(USBEndpoint):
                """Interrupt IN endpoint for guaranteed max latency"""

                number: int = 3
                direction: USBDirection = USBDirection.OUT
                transfer_type: USBTransferType = USBTransferType.BULK
                max_packet_size: int = 512

            class USBLoopbackIN3(USBEndpoint):
                """Interrupt IN endpoint for guaranteed max latency"""

                number: int = 3
                direction: USBDirection = USBDirection.IN
                transfer_type: USBTransferType = USBTransferType.BULK
                max_packet_size: int = 512

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
        if self.buffer[ep.number] is not None:
            self.send(ep.number, self.buffer[ep.number])
            self.buffer[ep.number] = None


if __name__ == "__main__":
    default_main(USBLoopback)
