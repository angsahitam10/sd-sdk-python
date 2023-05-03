import pytest


@pytest.mark.needsprogrammer
def test_initialize_device(initialized_device):
    assert initialized_device.device_info.IsValid


@pytest.mark.needsprogrammer
def test_configure_device(configured_device):
    assert configured_device.device_info.IsValid


# This allows you to override the fixture "programmer" and "side" with specific values
# (Note: We use 0 instead of sd.kLeft because we don't have access to the sd module at
#        test collection time.)
@pytest.mark.parametrize('programmer,side', [('Communication Accelerator Adaptor', 0)])   # 0=sd.kLeft
def test_initialize_device(initialized_device):
    assert initialized_device.device_info.IsValid
