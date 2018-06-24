#!/usr/bin/env python3
#
# facedancer-keyboard.py

from facedancer import FacedancerUSBApp
from facedancer.dev.switch_TAS import *

u = FacedancerUSBApp(verbose=5)
d = USBSwitchTASDevice(u, verbose=5)

d.connect()

try:
    d.run()
# SIGINT raises KeyboardInterrupt
except KeyboardInterrupt:
    d.disconnect()
