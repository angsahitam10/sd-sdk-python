#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
Sound Designer SDK wireless utility code.
"""
# Copyright (c) 2022 Semiconductor Components Industries, LLC
# (d/b/a ON Semiconductor). All Rights Reserved.
#
# This code is the property of ON Semiconductor and may not be redistributed
# in any form without prior written permission from ON Semiconductor. The
# terms of use and warranty for this code are covered by contractual
# agreements between ON Semiconductor and the licensee.
# ----------------------------------------------------------------------------
# $Revision:  $
# $Date:  $
# ----------------------------------------------------------------------------
import threading
import json
import logging
import time

from sd_sdk_python import get_product_manager
from sd_sdk_python.sd_sdk import DeviceInfo
import sd

logger = logging.getLogger("sd_sdk_wireless")


class SDKEventMonitor(object):
    def __init__(self,):
        self.listeners = []
        self.sdk_event_handler = get_product_manager().GetEventHandler()
        self.thread = threading.Thread(target=self.monitor_SDK)
        self.thread.daemon = True
        self.thread.start()

    def monitor_SDK(self, ):
        # This function runs in a background thread and notifies
        # any subscribed listeners of the events as they come in
        # from the SDK.
        while True:
            event = self.sdk_event_handler.GetEvent()
            data = self.parse_event_data(event.Data)
            self.notify(event.Type, data)

    def parse_event_data(self, event_data):
        # The JSON string for an event is a dict of list of dicts. In other words:
        #
        # {'Event': [{Data1 : Value1}, {Data2 : Value2}] }
        # 
        # This function flattens that into a simple dictionary of key:value pairs
        return_dict = {}
        for d in json.loads(event_data)['Event']:
            for key, val in d.items():
                return_dict[key] = val
        return return_dict

    def add_listener(self, item):
        # Add the item to the list of listeners to be notified of events
        if item not in self.listeners:
            self.listeners.append(item)

    def remove_listener(self, item):
        # Removes the item to the list of listeners to be notified of events
        if item in self.listeners:
            self.listeners.remove(item)

    def notify(self, event_type, event_data):
        for listener in self.listeners:
            listener.notify(event_type, event_data)


_event_monitor = SDKEventMonitor()


class SDKEventHandler:
    def listen_for_events(self, should_listen):
        if should_listen:
            _event_monitor.add_listener(self)
        else:
            _event_monitor.remove_listener(self)

    def __enter__(self):
        self.listen_for_events(True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.listen_for_events(False)

    def notify(self, event_type, event_data):
        pass


class ScanResultHandler(SDKEventHandler):
    def __init__(self, on_scan_event, listen=True) -> None:
        super().__init__()
        self.on_scan_event = on_scan_event
        self.listen_for_events(listen)

    @staticmethod
    def parse_manufacturing_data(data):
        # Valid manufacturing data is 5 bytes encoded as a string
        # of hex digits so the string will be 10 characters long
        if len(data) != 10:
            return data

        companyID_0 = int(data[2:4], 16)
        companyID_1 = int(data[0:2], 16)
        side = int(data[4:6], 16)
        mftrData_0 = int(data[8:], 16)
        mftrData_1 = int(data[6:8], 16)
        return { "company_id": (companyID_0 << 8) | companyID_1,
                 "side" : side,
                 "manufacturer_data" : (mftrData_0 << 8) | mftrData_1 }

    def notify(self, event_type, event_data):
        super().notify(event_type, event_data)
        if event_type == sd.kScanEvent:
            try:
                event_data['ManufacturingData'] = ScanResultHandler.parse_manufacturing_data(event_data['ManufacturingData'])
            except Exception as e:
                logger.error(e)

            self.on_scan_event(event_data)


class DeviceNotFoundError(Exception):
    pass

class InvalidStateError(Exception):
    pass


class WirelessCommAdaptor(object):
    """
    A class encapsulating the lifecycle of a wireless connection to a device.
    """
    def __init__(self, device_id, is_rsl10=False, on_event=None):
        self.device_id = device_id
        self.is_rsl10 = is_rsl10
        self.on_event = on_event
        self.state = sd.kDisconnected
        self.event = threading.Event()
        pm = get_product_manager()
        self.com_adaptor = pm.CreateWirelessCommunicationInterface(self.device_id)
        self.com_adaptor.SetEventHandler(pm.GetEventHandler())
        self.wireless_control = pm.GetWirelessControl()
        self.wireless_control.SetCommunicationAdaptor(self.com_adaptor)
        self.device_info = None
        _event_monitor.add_listener(self)

    def connect(self, timeout=10.0):
        if self.state != sd.kDisconnected:
            raise InvalidStateError(f"Device must be disconnected before attempting to connect")

        self.event.clear()
        logger.debug(f"Connecting to device {self.device_id}")
        self.com_adaptor.Connect()
        if not self.event.wait(timeout):
            raise RuntimeError(f"Failed to connect to device {self.device_id}")

        if self.is_rsl10:
            # !!! Work around firmware bug !!!
            logger.debug("Disconnecting and re-connecting due to firmware issue...")
            self.com_adaptor.Disconnect()
            self.event.clear()
            self.com_adaptor.Connect()
            if not self.event.wait(timeout):
                raise RuntimeError(f"Failed to connect to device {self.device_id}")
            # !!! Work around firmware bug !!!

        # Connection successful
        assert self.state == sd.kConnected
        self.com_adaptor.VerifyNvmWrites = True
        self.device_info = DeviceInfo(self.com_adaptor.DetectDevice())
        logger.debug(f"Connected to device {self.device_id}!")

    def disconnect(self, timeout=5.0):
        self.event.clear()
        if self.state == sd.kConnected:
            self.state = sd.kDisconnecting
            self.com_adaptor.Disconnect()
            if not self.event.wait(timeout):
                raise RuntimeError(f"Failed to disconnect from device {self.device_id}")
        self.device_info = None
        logger.debug(f"Disconnected from device {self.device_id}")

    def notify(self, event_type, event_data):
        if event_type == sd.kConnectionEvent and \
                event_data['DeviceID'] == self.device_id:

            if self.state in [sd.kDisconnected, sd.kConnecting] and \
                    int(event_data['ConnectionState']) == sd.kConnected:
                logger.debug(f"Got kConnected event for device {self.device_id}")
                self.state = sd.kConnected
                self.event.set()

            elif int(event_data['ConnectionState']) == sd.kDisconnected:
                logger.debug(f"Got kDisconnected event for device {self.device_id}")
                if self.state == sd.kDisconnecting:
                    self.state = sd.kDisconnected
                    self.event.set()
                else:
                    # This was unexpected
                    self.state = sd.kDisconnected
                    self.disconnect()

        if callable(self.on_event) and event_data['DeviceID'] == self.device_id:
            self.on_event(event_type, event_data)

    def close(self):
        self.disconnect()
        self.com_adaptor.CloseDevice()

    def __del__(self,):
        if _event_monitor is not None:
            _event_monitor.remove_listener(self)

    def __getattribute__(self, attr):
        # If a method doesn't exist here, try to find it in
        # the underlying com_adaptor.
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:
            return object.__getattribute__(self, 'com_adaptor').__getattribute__(attr)


def scan_for_devices(wireless_programmer_type,
                     com_port="",
                     side=sd.kLeft,
                     clear_bond_table=False,
                     scan_event_cb=None,
                     timeout=None):
    """
    Scans for wireless devices.

    wireless_programmer_type    One of kRSL10 or fNoahlinkWireless

    com_port                    Only used with RSL10 programmers

    side                        Only used with NOAHLink Wireless programmers

    clear_bond_table            If True, clear the bond table in the wireless programmer

    scan_event_cb               If a callable is passed, it is called for each scan event
                                as it arrives with a dictionary of the scan event data.
                                Return True to continue scanning or False to stop scanning.

    timeout                     Number of seconds to scan for before returning all scan
                                results. If not specified, scans forever (or until
                                scan_event_cb returns False).
    """
    pm = get_product_manager()

    class DummyScanResultHandler:
        def __init__(self, *args, **kwargs) -> None:
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    _scanner_obj = DummyScanResultHandler
    if callable(scan_event_cb):
        _scanner_obj = ScanResultHandler

    scanning = True
    def _cb(*args, **kwargs):
        nonlocal scanning
        scanning = scan_event_cb(*args, **kwargs)

    scan_results = None
    with _scanner_obj(_cb) as scanner:
        _res = pm.BeginScanForWirelessDevices(wireless_programmer_type, com_port, side, "", clear_bond_table)
        start = time.time()
        try:
            while scanning:
                if timeout is not None:
                    if time.time() - start > timeout:
                        raise TimeoutError("Scan timeout")
                time.sleep(0.001)
        except TimeoutError:
            logger.debug(f"Scan timed out after {timeout} seconds")
        finally:
            scan_results = pm.EndScanForWirelessDevices(_res)

    return scan_results


def scan_for_and_connect_to_device(device_id,
                                   wireless_programmer_type,
                                   com_port="",
                                   side=sd.kLeft,
                                   clear_bond_table=False,
                                   timeout=None,
                                   event_cb=None):
    """
    Scans for and connected to a specific wireless device.

    device_id                   The device ID (MAC address string or UUID) to connect to

    wireless_programmer_type    One of kRSL10 or kNoahlinkWireless

    com_port                    Only used with RSL10 programmers

    side                        Only used with NOAHLink Wireless programmers

    clear_bond_table            If True, clear the bond table in the wireless programmer

    timeout                     Number of seconds to scan for device before giving up.
                                If not specified, scans forever (or until the device
                                is found).

    event_cb                    Optional callback to call on SDK events
    """

    result = None

    def _on_scan_result(scan_result):
        nonlocal result
        if scan_result['DeviceID'] == device_id:
            logger.debug(f"Found device ID {device_id}: {scan_result}")
            result = scan_result
        # Scan until device is found
        return result is None

    scan_for_devices(wireless_programmer_type, com_port=com_port, side=side,
                     clear_bond_table=clear_bond_table, scan_event_cb=_on_scan_result,
                     timeout=timeout)

    if not result:
        raise DeviceNotFoundError(f"Failed to find device with ID {device_id}")

    assert result['DeviceID'] == device_id
    # Device found - connect to it
    adaptor = WirelessCommAdaptor(device_id, is_rsl10=wireless_programmer_type is sd.kRSL10, on_event=event_cb)
    adaptor.connect()
    return adaptor

def connect_to_device(device_id,
                      wireless_programmer_type,
                      timeout=10.0,
                      event_cb=None):
    """
    Attempts to connect to a specific wireless device.

    device_id                   The device ID (MAC address string or UUID) to connect to

    wireless_programmer_type    One of kRSL10 or kNoahlinkWireless

    timeout                     Number of seconds to wait for a response from the device
                                during the connect procedure.

    event_cb                    Optional callback to call on SDK events
    """
    adaptor = WirelessCommAdaptor(device_id, is_rsl10=wireless_programmer_type is sd.kRSL10, on_event=event_cb)
    adaptor.connect(timeout=timeout)
    return adaptor
