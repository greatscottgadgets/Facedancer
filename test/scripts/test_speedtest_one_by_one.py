#!/usr/bin/python3
# Copyright 2023 Quarkslab

"""
Tests the speed of a USB device with one EP IN and one EP OUT.
Data is sent to the EP OUT, and read from EP IN, without integrity checks.

NOTE : contrary to test_speedtest, this one sends/reads data of size the maximum packet size * max burst.
This was made for devices that can't handle libusb optimizations when sending large buffers.

This program can also write its results in a CSV, and repeat the measurement count times.
"""

import sys
import time
import random
import array
import argparse
import csv
import usb.core
import usb.util


ENDP_BURST_SIZE = 1
TOTAL_TRANSFER_SIZE_KB = 500

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Hydradancer speedtest", description="Measuring write/read transfer rate")
    csv_group = parser.add_argument_group(
        "CSV export", "Export results to CSV")
    csv_group.add_argument("--csv", action="store", help="Export to CSV")
    parser.add_argument("--count", default=1, action="store",
                        help="Number of runs", type=int)
    args = parser.parse_args()

    # find our device
    dev = usb.core.find(idVendor=0x610b, idProduct=0x4653)

    # was it found?
    if dev is None:
        raise ValueError('Device not found')

    if dev.speed == usb.util.SPEED_SUPER:
        ENDP_BURST_SIZE = 4
        print(f"USB30 Superspeed burst {ENDP_BURST_SIZE}")
    else:
        print("USB20")
        ENDP_BURST_SIZE = 1

    # set the active configuration. With no arguments, the first
    # configuration will be the active one
    # dev.set_configuration()

    print("Configuration of the device :")

    for cfg in dev:
        sys.stdout.write(str(cfg) + '\n')

    # get an endpoint instance
    cfg = dev.get_active_configuration()
    intf = cfg[(0, 0)]

    ep_in = usb.util.find_descriptor(
        intf,
        # match the first OUT endpoint
        custom_match=lambda e: \
        usb.util.endpoint_direction(e.bEndpointAddress) == \
        usb.util.ENDPOINT_IN)

    ep_out = usb.util.find_descriptor(
        intf,
        # match the first OUT endpoint
        custom_match=lambda e: \
        usb.util.endpoint_direction(e.bEndpointAddress) == \
        usb.util.ENDPOINT_OUT)

    assert ep_in is not None
    assert ep_out is not None
    assert ep_out.wMaxPacketSize == ep_in.wMaxPacketSize

    print("Reading ...")

    ROUNDS = 4
    SUCCESS = True

    endp_max_packet_size = ENDP_BURST_SIZE * ep_out.wMaxPacketSize
    buffer_size = int(((TOTAL_TRANSFER_SIZE_KB * 1e3) //
                      endp_max_packet_size) * endp_max_packet_size)
    buffer_out = array.array(
        'B', [int(random.random() * 255) for i in range(buffer_size)])
    buffer_in = array.array('B', [0 for i in range(buffer_size)])
    random_packet = array.array(
        'B', [int(random.random() * 255) for i in range(endp_max_packet_size)])

    write_transfer_time_diff = []
    read_transfer_time_diff = []

    for i in range(args.count):
        try:
            remaining_write = len(buffer_out)
            START = time.time_ns()
            while remaining_write != 0:
                packet_size = min(remaining_write, endp_max_packet_size)
                remaining_write -= ep_out.write(
                    random_packet[:packet_size], timeout=10000)
            STOP = time.time_ns()
            write_transfer_rate = len(buffer_out) / \
                ((STOP - START) * 1e-9) * 1e-6
            write_transfer_time_diff.append(STOP - START)
            print(f"Transfer rate write {write_transfer_rate} MB/s")
        except usb.core.USBTimeoutError:
            write_transfer_time_diff.append(-1)
            print("Error timeout")

        try:
            remaining_read = len(buffer_in)
            START = time.time_ns()
            while remaining_read != 0:
                packet_size = min(remaining_read, endp_max_packet_size)
                buffer = ep_in.read(packet_size, timeout=10000)
                remaining_read -= len(buffer)
            STOP = time.time_ns()
            read_transfer_rate = len(buffer_in) / \
                ((STOP - START) * 1e-9) * 1e-6
            read_transfer_time_diff.append(STOP - START)
            print(f"Transfer rate read {read_transfer_rate} MB/s")
        except usb.core.USBTimeoutError:
            read_transfer_time_diff.append(-1)
            print("Error timeout")

    if args.csv is not None:
        with open(args.csv, 'w', newline='', encoding='utf-8') as csvFile:
            fieldnames = [
                'Write(ns)', 'Read(ns)', 'Transfer size write (byte)', 'Transfer size read (byte)']
            writer = csv.DictWriter(
                csvFile, fieldnames=fieldnames, dialect='excel')

            writer.writeheader()
            for i in range(len(read_transfer_time_diff)):
                writer.writerow({'Write(ns)': write_transfer_time_diff[i], 'Read(ns)': read_transfer_time_diff[i], 'Transfer size write (byte)': len(
                    buffer_out), 'Transfer size read (byte)': len(buffer_in)})
