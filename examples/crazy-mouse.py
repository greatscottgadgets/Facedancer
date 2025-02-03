#!/usr/bin/env python3
#
# This file is part of FaceDancer.
#
""" USB mouse device example, makes the mouse go crazy on screen """

import asyncio

from facedancer import main
from facedancer.devices.mouse import USBMouseDevice

device = USBMouseDevice()


async def crazy_mouse():
    """Makes the mouse oscillate"""
    while 1:
        device.set_x(-10)
        await asyncio.sleep(0.1)
        device.set_x(10)
        await asyncio.sleep(0.1)


main(device, crazy_mouse())
