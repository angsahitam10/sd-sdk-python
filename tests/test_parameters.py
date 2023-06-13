import pytest
import pathlib
import time


@pytest.fixture
def synced_device(sd, configured_device):
    assert len(configured_device.product.Memories) == 8
    # Configure for a pure tone input signal
    configured_device.set_input_signal_type(sd.kPureTone)
    # Switch to memory 1
    configured_device.set_current_memory(sd.kNvmMemory1)
    # Sync all parameters from the device
    configured_device.restore_all_parameters()
    assert configured_device.get_current_memory() == sd.kNvmMemory1
    yield configured_device

def test_not_initialized_fail(sd, product):
    with pytest.raises(Exception) as exc_info:
        assert product.Ear in [0, 1]
    assert exc_info.type.__name__ == "DeviceError" and str(exc_info.value) == "E_NOT_INITIALIZED"


# This allows you to override the fixture "programmer" and "side" with specific values
# (Note: We use 0 instead of sd.kLeft because we don't have access to the sd module at
#        test collection time.)
# @pytest.mark.parametrize('programmer,side', [('Communication Accelerator Adaptor', 0)])   # 0=sd.kLeft
# @pytest.mark.parametrize('product_name', ['E7111V2'])
@pytest.mark.needsprogrammer
def test_count_parameters(configured_device):
    system_param_count, memory_param_counts = configured_device.count_parameters()
    # print(system_param_count, memory_param_counts)
    # 650 [592, 592, 592, 592, 592, 592, 592, 592]
    assert system_param_count == 650
    assert len(memory_param_counts) == 8
    for c in memory_param_counts:
        assert c == 592


@pytest.mark.skip
@pytest.mark.needsprogrammer
def test_delete_bond_table(configured_device):
    configured_device.interface.ClearBondTableOnDevice()
    #TODO: Need a means of confirming the bond table is deleted...


@pytest.mark.skip
# @pytest.mark.parametrize('param_file', [('EC_Left.param',)])
@pytest.mark.parametrize('param_file', ['EC_Right.param'])
@pytest.mark.needsprogrammer
def test_load_param_file(sd, configured_device, param_file):
    assert len(configured_device.product.Memories) == 8
    this_path = pathlib.Path(__file__).parent.resolve()

    configured_device.interface.MuteDuringCommunication = False

    configured_device.mute()

    # Configure for a pure tone input signal
    configured_device.set_input_signal_type(sd.kPureTone)

    # Switch to memory 1
    configured_device.set_current_memory(sd.kNvmMemory1)

    # Sync all parameters from the device
    configured_device.restore_all_parameters()

    configured_device.load_param_file(str(this_path / param_file), True, True, True)

    configured_device.unmute()

    # Reset the device (this must be the last thing we do as the device will disconnect)
    configured_device.reset()


@pytest.mark.skip
@pytest.mark.needsprogrammer
def test_load_param_file_async(sd, configured_device):
    from sd_sdk_python import sd_sdk

    assert len(configured_device.product.Memories) == 8
    this_path = pathlib.Path(__file__).parent.resolve()

    configured_device.interface.MuteDuringCommunication = False

    configured_device.mute()

    # Configure for a pure tone input signal
    configured_device.set_input_signal_type(sd.kPureTone)

    # Switch to memory 1
    configured_device.set_current_memory(sd.kNvmMemory1)

    # Sync all parameters from the device
    configured_device.restore_all_parameters()

    _async = configured_device.product.BeginLoadParamFile(str(this_path / 'EC_Right.param'), True, True, True)
    result = sd_sdk.wait_for_async(timeout_seconds=30.0)

    configured_device.unmute()

    # Reset the device (this must be the last thing we do as the device will disconnect)
    configured_device.reset()


@pytest.mark.needsprogrammer
def test_read_scratch_memory(sd, synced_device):
    data = synced_device.read_scratch_memory()
    print([hex(w) for w in data], len(data))


def read_gap_device_name_parameters_from_RAM(device):
    gap_device_name0 = device.get_global_parameter_in_RAM('X_RF_GAPDeviceName0')
    gap_device_name1 = device.get_global_parameter_in_RAM('X_RF_GAPDeviceName1')
    gap_device_name2 = device.get_global_parameter_in_RAM('X_RF_GAPDeviceName2')
    gap_device_name3 = device.get_global_parameter_in_RAM('X_RF_GAPDeviceName3')
    gap_device_name4 = device.get_global_parameter_in_RAM('X_RF_GAPDeviceName4')
    gap_device_name5 = device.get_global_parameter_in_RAM('X_RF_GAPDeviceName5')
    gap_device_name6 = device.get_global_parameter_in_RAM('X_RF_GAPDeviceName6')
    gap_device_name7 = device.get_global_parameter_in_RAM('X_RF_GAPDeviceName7')
    return [gap_device_name0, gap_device_name1, gap_device_name2, gap_device_name3, gap_device_name4, gap_device_name5, gap_device_name6, gap_device_name7]

def write_gap_device_name_parameters_in_RAM(device, new_parameters):
    for i, param in enumerate(new_parameters):
        device.set_global_parameter_in_EEPROM(f'X_RF_GAPDeviceName{i}', param)

def read_device_name_parameters_from_RAM(device):
    device_name0 = device.get_global_parameter_in_RAM('X_RF_DeviceName0')
    device_name1 = device.get_global_parameter_in_RAM('X_RF_DeviceName1')
    device_name2 = device.get_global_parameter_in_RAM('X_RF_DeviceName2')
    device_name3 = device.get_global_parameter_in_RAM('X_RF_DeviceName3')
    device_name4 = device.get_global_parameter_in_RAM('X_RF_DeviceName4')
    device_name5 = device.get_global_parameter_in_RAM('X_RF_DeviceName5')
    device_name6 = device.get_global_parameter_in_RAM('X_RF_DeviceName6')
    device_name7 = device.get_global_parameter_in_RAM('X_RF_DeviceName7')
    return [device_name0, device_name1, device_name2, device_name3, device_name4, device_name5, device_name6, device_name7]

def write_device_name_parameters_in_RAM(device, new_parameters):
    for i, param in enumerate(new_parameters):
        device.set_global_parameter_in_EEPROM(f'X_RF_DeviceName{i}', param)

@pytest.mark.needsprogrammer
def test_set_device_name(synced_device):
    original_parameters = read_device_name_parameters_from_RAM(synced_device)
    original_device_name = synced_device.parameters_to_device_name(original_parameters)
    assert synced_device.device_name_to_parameters(original_device_name) == original_parameters

    # Override device name
    new_name = 'Hörgerät'
    assert original_device_name != new_name
    new_parameters = synced_device.device_name_to_parameters(new_name)
    write_device_name_parameters_in_RAM(synced_device, new_parameters)

    written_parameters = read_device_name_parameters_from_RAM(synced_device)
    written_name = synced_device.parameters_to_device_name(written_parameters)

    assert written_name == new_name

    # Restore original device name
    write_device_name_parameters_in_RAM(synced_device, original_parameters)
    assert read_device_name_parameters_from_RAM(synced_device) == original_parameters


@pytest.mark.needsprogrammer
def test_set_gap_device_name(synced_device):
    original_parameters = read_gap_device_name_parameters_from_RAM(synced_device)
    original_gap_device_name = synced_device.parameters_to_device_name(original_parameters)
    assert synced_device.device_name_to_parameters(original_gap_device_name) == original_parameters

    # Override device name
    new_name = 'Hörgerät'
    assert original_gap_device_name != new_name
    new_parameters = synced_device.device_name_to_parameters(new_name)
    write_device_name_parameters_in_RAM(synced_device, new_parameters)

    written_parameters = read_device_name_parameters_from_RAM(synced_device)
    written_name = synced_device.parameters_to_device_name(written_parameters)

    assert written_name == new_name

    # Restore original device name
    write_device_name_parameters_in_RAM(synced_device, original_parameters)
    assert read_device_name_parameters_from_RAM(synced_device) == original_parameters


@pytest.mark.needsprogrammer
def test_device_name_encode_decode(synced_device):
    name = 'HörgerätHörgertttt'
    encoded_parameters = synced_device.device_name_to_parameters(name)
    expected_parameters = [0x48c3b6, 0x726765, 0x72c3a4, 0x7448c3, 0xb67267, 0x657274, 0x747474, 0x0]
    assert synced_device.parameters_to_device_name(encoded_parameters) == name

    name = 'HörgerätHörgertttä'
    encoded_parameters = synced_device.device_name_to_parameters(name)
    expected_parameters = [0x48c3b6, 0x726765, 0x72c3a4, 0x7448c3, 0xb67267, 0x657274, 0x7474c3, 0xa40000]
    assert synced_device.parameters_to_device_name(encoded_parameters) == name

    name = 'HörgerätHörgertttä1'
    encoded_parameters = synced_device.device_name_to_parameters(name)
    # Name should be clipped to 22 characters
    expected_parameters = [0x48c3b6, 0x726765, 0x72c3a4, 0x7448c3, 0xb67267, 0x657274, 0x7474c3, 0xa40000]
    assert synced_device.parameters_to_device_name(encoded_parameters) != name
    assert synced_device.parameters_to_device_name(encoded_parameters) == name[:-1]

    name = 'HörgerätHörgertttää'
    encoded_parameters = synced_device.device_name_to_parameters(name)
    expected_parameters = [0x48c3b6, 0x726765, 0x72c3a4, 0x7448c3, 0xb67267, 0x657274, 0x7474c3, 0xa40000]
    assert encoded_parameters == expected_parameters
    assert synced_device.parameters_to_device_name(encoded_parameters) != name
    # Name should be truncated to 22 characters
    assert synced_device.parameters_to_device_name(encoded_parameters) == name[:-1]

    name = 'HörgerätHörgerttää'
    encoded_parameters = synced_device.device_name_to_parameters(name)
    expected_parameters = [0x48c3b6, 0x726765, 0x72c3a4, 0x7448c3, 0xb67267, 0x657274, 0x74c3a4, 0x0]
    assert encoded_parameters == expected_parameters
    assert synced_device.parameters_to_device_name(encoded_parameters) != name
    # Name should be truncated to 22 characters, but to the nearest UTF-8 encoded byte
    assert synced_device.parameters_to_device_name(encoded_parameters) == name[:-1]


@pytest.mark.needsprogrammer
def test_device_name_parameters(synced_device):
    name = 'abcdefghijklmnopqrstuv'
    encoded_parameters = synced_device.device_name_to_parameters(name)
    assert encoded_parameters == [6382179, 6579558, 6776937, 6974316, 7171695, 7369074, 7566453, 7733248]
