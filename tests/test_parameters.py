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
    # Switch to memory 1 (non-EC memory)
    configured_device.set_current_memory(sd.kNvmMemory1)
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
    # 642 [592, 592, 592, 592, 592, 592, 592, 592]
    assert system_param_count == 642
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


@pytest.mark.skip
@pytest.mark.needsprogrammer
def test_read_scratch_memory(sd, synced_device):
    data = synced_device.read_scratch_memory()
    print([hex(w) for w in data], len(data))


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

@pytest.mark.skip
@pytest.mark.needsprogrammer
def test_set_device_name(sd, synced_device):
    original_parameters = read_device_name_parameters_from_RAM(synced_device)
    original_device_name = synced_device.parameters_to_device_name(original_parameters)
    assert synced_device.device_name_to_parameters(original_device_name) == original_parameters

    # Override device name
    new_name = 'Hörgerät'
    new_parameters = synced_device.device_name_to_parameters(new_name)
    write_device_name_parameters_in_RAM(synced_device, new_parameters)

    written_parameters = read_device_name_parameters_from_RAM(synced_device)
    written_name = synced_device.parameters_to_device_name(written_parameters)

    assert written_name == new_name

    # Restore original device name
    write_device_name_parameters_in_RAM(synced_device, original_parameters)
    assert read_device_name_parameters_from_RAM(synced_device) == original_parameters

######################
## Reference code....
######################
def connect_device(ezairo_klass, sd, communication_interface, product, product_name):
    device_info = communication_interface.DetectDevice()
    assert device_info is not None
    assert device_info.IsValid
    assert device_info.FirmwareId == product_name

    if not product.InitializeDevice(communication_interface):
        product.ConfigureDevice()

    assert device_info.LibraryId == product.Definition.LibraryId
    assert device_info.ProductId == product.Definition.ProductId
    return ezairo_klass(sd, communication_interface, device_info, product)

def program_binaural_half(configured_device, param_file, peer_address):
    this_path = pathlib.Path(__file__).parent.resolve()

    configured_device.interface.MuteDuringCommunication = False

    configured_device.mute()

    # Configure for a pure tone input signal
    configured_device.set_input_signal_type(configured_device.sd.kPureTone)

    # Switch to memory 1
    configured_device.set_current_memory(configured_device.sd.kNvmMemory1)

    # Sync all parameters from the device
    configured_device.restore_all_parameters()

    # Load the parameters from the param file, but don't configure
    # (just burn the voice alerts and manufacturing data)
    configured_device.load_param_file(str(this_path / param_file),
                                      configure_device=False,
                                      write_manufacturer_data=True,
                                      write_voice_alerts=True)

    # Override the peer address
    configured_device.set_parameter_value(configured_device.sd.kSystemNvmMemory, 'X_RF_BinauralPeerAddress2', peer_address & 0xFFFFFF)
    configured_device.set_parameter_value(configured_device.sd.kSystemNvmMemory, 'X_RF_BinauralPeerAddress1', peer_address >> 24)
    configured_device.burn_all_parameters()
    configured_device.interface.ClearBondTableOnDevice()

    configured_device.unmute()

    # Reset the device (this must be the last thing we do as the device will disconnect)
    configured_device.reset()


@pytest.mark.skip
@pytest.mark.needsprogrammer
def test_program_binaural_pair(sd, Ezairo, communication_interface, product, product_name):
    print("")
    print("This test will flash two devices as a binaural pair.")
    print("In order to do this, it will need to read the MAC addresses from both devices.")
    print("Power on the device you want to be the peripheral (right ear) and press any key when ready.")
    input()

    peripheral = connect_device(Ezairo, sd, communication_interface, product, product_name)
    peripheral_address = int(peripheral.product.DeviceMACAddress, 16)
    peripheral.product.CloseDevice()
    print(f"Peripheral MAC: {hex(peripheral_address)}")

    print("Power off the peripheral and power on the central (left ear) and press any key when ready.")
    input()

    central = connect_device(Ezairo, sd, communication_interface, product, product_name)
    central_address = int(central.product.DeviceMACAddress, 16)
    print(f"Central MAC: {hex(central_address)}")
    # Program the Central
    print("Programming central...")
    program_binaural_half(central, 'EC_Left.param', peripheral_address)
    central.product.CloseDevice()

    print("Power off the central and power on the peripheral (right ear) and press any key when ready.")
    input()
    peripheral = connect_device(Ezairo, sd, communication_interface, product, product_name)
    # Program the Peripheral
    print("Programming peripheral...")
    program_binaural_half(peripheral, 'EC_Right.param', central_address)
    peripheral.product.CloseDevice()
    print("Done!")