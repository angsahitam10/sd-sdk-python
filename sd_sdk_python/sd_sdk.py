#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
A Python module exposing useful utilities for the Sound Designer SDK.
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

import time
from dataclasses import dataclass
import sys
import struct


def convert_value(value):
    """Convert an SDK value to Python"""
    if value.lower() == "true":
        return True
    elif value.lower() == 'false':
        return False
    elif value.find('.') >= 0:
        return float(value)
    else:
        return int(value)

@dataclass
class DeviceInfo:
    _info: object
    # The rest of these parameters are initialized from the
    # '_info' object at creation time (see __post_init__)
    library_id: int = 0
    product_id: int = 0
    chip_id: int = 0
    chip_version: int = 0
    hybrid_id: int = 0
    firmware_id: str = ""
    firmware_version: str = ""
    serial_id: int = 0
    valid: bool = False
    locked: bool = False
    radio_application_version: str = ""
    radio_bootloader_version: str = ""
    radio_soft_device_version: str = ""
    hybrid_serial: int = 0
    hybrid_revision: int = 0
    hybrid_tester: int = 0

    def __post_init__(self):
        assert self._info is not None
        self.library_id = self._info.LibraryId
        self.product_id = self._info.ProductId
        self.chip_id = self._info.ChipId
        self.chip_version = self._info.ChipVersion
        self.hybrid_id = self._info.HybridId
        self.firmware_id = self._info.FirmwareId
        self.firmware_version = self._info.FirmwareVersion
        self.serial_id = self._info.SerialId
        self.valid = self._info.IsValid
        self.locked = self._info.ParameterLockState
        self.radio_application_version = self._info.RadioApplicationVersion
        self.radio_bootloader_version = self._info.RadioBootloaderVersion
        self.radio_soft_device_version = self._info.RadioSoftDeviceVersion
        self.hybrid_serial = self._info.HybridSerial
        self.hybrid_revision = self._info.HybridRevision
        self.hybrid_tester = self._info.HybridTester

    def to_dict(self,) -> dict:
        return {k:v for k,v in self.__dict__.items() if not k.startswith('_')}

@dataclass
class Ezairo:
    sd: object
    interface: object
    device_info: object
    product: object

    def __post_init__(self):
        if type(self.device_info) == self.sd.DeviceInfo:
            # Convert to richer dataclass automatically
            self.device_info = DeviceInfo(self.device_info)

    def load_param_file(self, param_file, configure_device=False, write_manufacturer_data=False, write_voice_alerts=False):
        if self.product is not None:
            self.product.LoadParamFile(str(param_file), configure_device, write_manufacturer_data, write_voice_alerts)

    def reset(self,):
        if self.product is not None:
            self.product.ResetDevice()

    def mute(self,):
        if self.product is not None:
            self.product.MuteDevice(True)

    def unmute(self,):
        if self.product is not None:
            self.product.MuteDevice(False)

    def set_input_signal_type(self, signal_type):
        if self.product is not None:
            self.product.InputSignal = signal_type

    def get_current_memory(self,):
        if self.product is not None:
            return self.product.CurrentMemory

    def set_current_memory(self, memory_number, read_parameters=False):
        if self.product is not None:
            self.product.SwitchToMemory(memory_number)
            if self.interface is not None and read_parameters:
                self.product.ReadParameters(self.sd.kActiveMemory)

    def get_parameter_value(self, memory_number, param_name):
        param = self.find_parameter(memory_number, param_name)
        value = None
        if param is not None:
            if param.Type in [self.sd.kInteger, self.sd.kIndexedList, self.sd.kIndexedTextList, self.sd.kByte]:
                value = param.Value
            elif param.Type == self.sd.kBoolean:
                value = param.BooleanValue
            elif param.Type == self.sd.kDouble:
                value = param.DoubleValue
            else:
                raise "Unknown parameter type."

        # print("%s: %s" % (param_name, value))
        return value

    def set_parameter_value(self, memory_number, param_name, value):
        param = self.find_parameter(memory_number, param_name)
        if param is not None:
            if param.Type in [self.sd.kInteger, self.sd.kIndexedList, self.sd.kIndexedTextList, self.sd.kByte]:
                param.Value = value
            elif param.Type == self.sd.kBoolean:
                param.BooleanValue = value
            elif param.Type == self.sd.kDouble:
                param.DoubleValue = value
            else:
                raise "Unknown parameter type."
            #print("Setting %s to %s" % (param_name, value))

    def find_parameter(self, memory_number, param_name):
        if self.product is not None:
            if memory_number == self.sd.kSystemNvmMemory or memory_number == self.sd.kSystemActiveMemory:
                return self.product.SystemMemory.Parameters.GetById(param_name)
            else:
                if memory_number == self.sd.kActiveMemory:
                    memory_number = self.product.CurrentMemory
                return self.product.Memories[memory_number].Parameters.GetById(param_name)

    def find_parameters_with_prefix(self, memory_number, param_name_prefix):
        parameters_found = []
        if self.product is not None:
            if memory_number == self.sd.kSystemNvmMemory or memory_number == self.sd.kSystemActiveMemory:
                for p in self.product.SystemMemory.Parameters:
                    if p.Id.startswith(param_name_prefix):
                        parameters_found.append(p)
            else:
                if memory_number == self.sd.kActiveMemory:
                    memory_number = self.product.CurrentMemory
                for p in self.product.Memories[memory_number].Parameters:
                    if p.Id.startswith(param_name_prefix):
                        parameters_found.append(p)
        return parameters_found

    def count_parameters(self,):
        if self.product is not None:
            return (len(self.product.SystemMemory.Parameters), 
                    [len(self.product.Memories[w].Parameters) for w in range(len(self.product.Memories))])
        return (0,[0,])

    def restore_all_parameters(self,):
        if self.product is not None and self.interface is not None:
            # Back up current memory
            current_memory = self.get_current_memory()

            self.restore_system_parameters()
            for i in range(len(self.product.Memories)):
                self.restore_profile_parameters(i)

            # Restore original memory
            self.set_current_memory(current_memory, read_parameters=False)

    def restore_system_parameters(self,):
        if self.product is not None and self.interface is not None:
            self.product.ReadParameters(self.sd.kSystemNvmMemory)

    def restore_profile_parameters(self, memory):
        if self.product is not None and self.interface is not None:
            self.product.ReadParameters(memory)

    def burn_all_parameters(self,):
        if self.product is not None and self.interface is not None:
            self.product.WriteParameters(self.sd.kSystemNvmMemory)
            for i in range(len(self.product.Memories)):
                self.product.WriteParameters(i)

    def write_voice_alert_data(self, voice_alert_data: bytes):
        if self.product is not None and self.interface is not None:
            data_len = len(voice_alert_data)
            assert data_len <= self.product.ReadVoiceAlertsTotalMemory(), f"Not enough space for {data_len} bytes of voice alerts"
            self.product.WriteVoiceAlert(data_len, voice_alert_data)

    def write_scratch_memory(self, scratch_memory: list[int]):
        if self.product is not None and self.interface is not None:
            scratch_data = struct.pack('>' +'I'*len(scratch_memory), *scratch_memory)
            data_len = len(scratch_data)
            assert data_len <= self.product.Definition.ManufacturerDataAreaLength, f"Not enough space for {data_len} bytes of scratch memory"
            self.product.WriteManufacturerData(0, data_len, scratch_data)

    def read_scratch_memory(self,):
        if self.product is not None and self.interface is not None:
            return self.product.ReadManufacturerData(0, self.product.Definition.ManufacturerDataAreaLength)

    def get_profile_parameter_in_RAM(self, param_name):
        return self.get_parameter_value(self.sd.kActiveMemory, param_name)

    def set_profile_parameter_in_RAM(self, param_name, value):
        self.set_parameter_value(self.sd.kActiveMemory, param_name, value)
        self.product.WriteParameters(self.sd.kActiveMemory)

    def get_global_parameter_in_RAM(self, param_name):
        return self.get_parameter_value(self.sd.kSystemActiveMemory, param_name)

    def set_global_parameter_in_RAM(self, param_name, value):
        self.set_parameter_value(self.sd.kSystemActiveMemory, param_name, value)
        self.product.WriteParameters(self.sd.kSystemActiveMemory)

    def get_profile_parameter_in_EEPROM(self, param_name, nvm_memory):
        if nvm_memory not in [self.sd.kNvmMemory0, self.sd.kNvmMemory1, self.sd.kNvmMemory2, self.sd.kNvmMemory3, 
                              self.sd.kNvmMemory4, self.sd.kNvmMemory5, self.sd.kNvmMemory6, self.sd.kNvmMemory7]:
            raise RuntimeError("%d is not a supported EEPROM memory!" % nvm_memory)
        self.restore_profile_parameters(nvm_memory)
        return self.get_parameter_value(nvm_memory, param_name)

    def set_profile_parameter_in_EEPROM(self, param_name, value, nvm_memory):
        if nvm_memory not in [self.sd.kNvmMemory0, self.sd.kNvmMemory1, self.sd.kNvmMemory2, self.sd.kNvmMemory3, 
                              self.sd.kNvmMemory4, self.sd.kNvmMemory5, self.sd.kNvmMemory6, self.sd.kNvmMemory7]:
            raise RuntimeError("%d is not a supported EEPROM memory!" % nvm_memory)
        self.set_parameter_value(nvm_memory, param_name, value)
        self.product.WriteParameters(nvm_memory)

    def set_global_parameter_in_EEPROM(self, param_name, value):
        self.set_parameter_value(self.sd.kSystemNvmMemory, param_name, value)
        self.product.WriteParameters(self.sd.kSystemNvmMemory)

    def get_global_parameter_in_EEPROM(self, param_name):
        self.restore_system_parameters()
        return self.get_parameter_value(self.sd.kSystemNvmMemory, param_name)

    def dump_parameters(self, file_obj=None):
        if file_obj is None:
            file_obj = sys.stdout

        if self.product is not None:
            # Dump all system parameters
            for p in self.product.SystemMemory.Parameters:
                file_obj.write("%s=%s\n" % (p.Id, self.get_parameter_value(self.sd.kSystemNvmMemory, p.Id)))
            # Dump all parameters in all memories
            i = 0
            for m in self.product.Memories:
                for p in m.Parameters:
                    file_obj.write("%s=%s\n" % (p.Id, self.get_parameter_value(i, p.Id)))
                i += 1

    @staticmethod
    def parameters_to_device_name(list_of_parameters):
        assert len(list_of_parameters) <= 8
        name = b''
        for param in list_of_parameters:
            name += param.to_bytes(3, 'big')
        return name.decode('utf-8').strip('\x00')

    @staticmethod
    def device_name_to_parameters(name):
        params = [0]*8
        encoded_bytes = []
        for character in name:
            enc = character.encode('utf-8')
            # Clip length to 22 bytes (maximum allowable name length)
            if (len(encoded_bytes) + len(enc)) > 22:
                break
            encoded_bytes += [int(w) for w in enc]

        # Pack encoded_bytes into 24-bit parameters
        for i in range(0, len(encoded_bytes), 3):
            value = 0
            substr = encoded_bytes[i:i+3]
            for j, char in enumerate(substr):
                value |= (char << (16 - j*8))
            params[i // 3] = value
        return params

def wait_for_async(_async, timeout_seconds=1.0, sleep_time_seconds=0.01):
    """Waits for an AsyncResult to finish"""
    while not _async.IsFinished and timeout > 0:
        time.sleep(sleep_time_seconds)
        timeout -= sleep_time_seconds

    if timeout <= 0:
        raise RuntimeError("Error: Timed out waiting for async!")

    return _async.GetResult()
