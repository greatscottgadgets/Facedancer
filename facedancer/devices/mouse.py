"""
Create a basic mouse device with three buttons and two axis
"""

from . import default_main
from ..                       import *
from ..classes.hid.descriptor import *
from ..classes.hid.usage import *


@use_inner_classes_automatically
class USBMouseDevice(USBDevice):
    """Simple USB mouse device."""

    name: str = "USB Mouse Device"
    product_string: str = "Non-suspicious Mouse"

    # Local mouse state
    _x: int = 0
    _y: int = 0
    _wheel: int = 0
    _trigger: bool = False
    _secondary: bool = False
    _tertiary: bool = False

    class MouseConfiguration(USBConfiguration):
        """Primary configuration : act as a mouse"""

        max_power: int = 100
        self_powered: bool = False
        supports_remote_wakeup: bool = True

        class MouseInterface(USBInterface):
            """Core HID interface for our mouse"""

            name: str = "Generic USB mouse interface"
            class_number: int = 3  # Human Interface Device class number

            class MouseEventEndpoint(USBEndpoint):
                """Interrupt IN endpoint for guaranteed max latency"""

                number: int = 1
                direction: USBDirection = USBDirection.IN
                transfer_type: USBTransferType = USBTransferType.INTERRUPT
                interval: int = 10

            class MouseHIDDescriptor(USBClassDescriptor):
                """Container for the mouse HID report descriptors"""

                number: int = USBDescriptorTypeNumber.HID

                # raw descriptor fields
                bLength: bytes = b"\x09"
                bHIDDescriptorType: bytes = b"\x21"  # HID descriptor type
                bcdHID: bytes = b"\x11\x01"  # HID 1.11
                bCountryCode: bytes = b"\x00"
                bNumDescriptors: bytes = b"\x01"
                bDescriptorType: bytes = b"\x22"  # Report descriptor type
                wDescriptorLength: bytes = (
                    b"\x3e\x00"  # 62 -- TODO should be computed automatically
                )

                raw: bytes = (
                    bLength
                    + bHIDDescriptorType
                    + bcdHID
                    + bCountryCode
                    + bNumDescriptors
                    + bDescriptorType
                    + wDescriptorLength
                )

            class MouseReportDescriptor(HIDReportDescriptor):
                """Defines the mouse report descriptor :
                * X/Y axis
                * three buttons (trigger/primary, secondary, tertiary)
                """

                fields: tuple = (
                    USAGE_PAGE(HIDUsagePage.GENERIC_DESKTOP),
                    USAGE(HIDGenericDesktopUsage.MOUSE),
                    COLLECTION(HIDCollection.APPLICATION),
                    USAGE(HIDGenericDesktopUsage.POINTER),
                    COLLECTION(HIDCollection.PHYSICAL),
                    USAGE_PAGE(HIDUsagePage.BUTTONS),
                    USAGE_MINIMUM(0x01),  # see HID 1.11
                    USAGE_MAXIMUM(0x03),
                    LOGICAL_MINIMUM(0x0),
                    LOGICAL_MAXIMUM(0x01),
                    REPORT_SIZE(1),
                    REPORT_COUNT(3),
                    INPUT(variable=True, relative=False),
                    REPORT_SIZE(5),
                    REPORT_COUNT(1),
                    INPUT(variable=True, constant=True),
                    USAGE_PAGE(HIDUsagePage.GENERIC_DESKTOP),
                    USAGE(HIDGenericDesktopUsage.X),
                    USAGE(HIDGenericDesktopUsage.Y),
                    LOGICAL_MINIMUM(0x81),  # -127
                    LOGICAL_MAXIMUM(0x7F),  # 127
                    REPORT_SIZE(8),
                    REPORT_COUNT(2),
                    INPUT(variable=True, relative=True),
                    USAGE(HIDGenericDesktopUsage.WHEEL),
                    LOGICAL_MINIMUM(0x81),  # -127
                    LOGICAL_MAXIMUM(0x7F),  # 127
                    REPORT_SIZE(8),
                    REPORT_COUNT(1),
                    INPUT(variable=True, relative=True),
                    END_COLLECTION(),
                    END_COLLECTION(),
                )

    @class_request_handler(number=USBStandardRequests.GET_INTERFACE)
    @to_this_interface
    def handle_get_interface_request(self, request):
        # Silently stall GET_INTERFACE class requests.
        request.stall()

    def set_x(self, x: int):
        """Set X axis translation"""
        self._x = x

    def set_y(self, y: int):
        """Set Y axis translation"""
        self._y = y

    def set_wheel(self, rotation: int):
        """Set rotation"""
        self._wheel = rotation

    def set_trigger(self, down: bool):
        """Set down to True to trigger primary button"""
        self._trigger = down

    def set_secondary(self, down: bool):
        """Set down to True to trigger secondary button"""
        self._secondary = down

    def set_tertiary(self, down: bool):
        """Set down to True to trigger tertiary button"""
        self._tertiary = down

    def _get_buttons_state(self):
        """Create buttons report from current state"""
        state = 0x00

        if self._trigger:
            state |= 1 << 0
        if self._secondary:
            state |= 1 << 1
        if self._tertiary:
            state |= 1 << 2

        return state

    def handle_data_requested(self, endpoint: USBEndpoint):
        """Provide data once per host request."""
        endpoint.send(
            self._get_buttons_state().to_bytes(1, "little")
            + self._x.to_bytes(1, "little", signed=True)
            + self._y.to_bytes(1, "little", signed=True)
            + self._wheel.to_bytes(1, "little", signed=True)
        )


if __name__ == "__main__":
    default_main(USBMouseDevice)
