import pytest
from pathlib import Path
import os
from dataclasses import dataclass


def set_sdk_root(value):
    path_value = Path(value)
    if not path_value.exists() or not path_value.is_dir():
        raise pytest.UsageError(f"{value} is not a valid path")

    os.environ['SD_SDK_ROOT'] = str(path_value)

    return path_value


def pytest_addoption(parser):
    parser.addoption(
        "--sdk-root",
        action="store",
        default=None,
        help="Path to the Sound Designer SDK root folder (or set 'SD_SDK_ROOT' in your environment)",
        type=set_sdk_root,
    )
    parser.addoption(
        "--programmer",
        action="store",
        default=None,
        help="Specify which programmer to use (one of ['CAA', 'DSP3', 'Promira'])",
        choices=("CAA", "DSP3", "Promira"),
    )
    parser.addoption(
        "--side",
        action="store",
        default="left",
        help="Specify which side to use (one of ['left', 'right'])",
        choices=("left", "right"),
    )
    parser.addoption(
        "--interface-options",
        action="store",
        default=None,
        help="Options to pass to the communication interface",
    )
    parser.addoption(
        "--product",
        action="store",
        default="E7160SL",
        help="Which product to use (one of ['E7111V2', 'E7160SL'])",
        choices=('E7111V2', 'E7160SL'),
    )
    parser.addoption(
        "--verify-nvm-writes", action="store_true", default=False, help="Verify all NVM writes"
    )

@pytest.fixture(scope="session")
def sd():
    from sd_sdk_python import sd as _sd
    yield _sd

@pytest.fixture(scope="session")
def Ezairo(sd):
    assert sd.kRSL10 == 2
    from sd_sdk_python.sd_sdk import Ezairo as _ezairo
    yield _ezairo

@pytest.fixture(scope="session")
def product_manager():
    from sd_sdk_python import get_product_manager
    yield get_product_manager()

@pytest.fixture(scope="session")
def product_name(request):
    return request.config.getoption('--product')

@pytest.fixture
def product_library(product_manager, product_name):
    sdk_root = Path(os.environ['SD_SDK_ROOT'])
    return product_manager.LoadLibraryFromFile(str(sdk_root / f"products/{product_name}.library"))

@pytest.fixture
def product(product_manager, product_library):
    product = product_library.Products[0].CreateProduct()
    return product


####################################################################
## Fixtures related to a programmer specified on the command line ##
####################################################################

def pytest_configure(config):
    config.addinivalue_line("markers", "needsprogrammer: Marks tests requiring a specific programmer")

def pytest_collection_modifyitems(config, items):
    if config.getoption("--programmer") is not None:
        return
    skip_needsprogrammer = pytest.mark.skip(reason="need --programmer option to run")
    for item in items:
        if "needsprogrammer" in item.keywords:
            item.add_marker(skip_needsprogrammer)

@pytest.fixture
def programmer(request):
    programmer = request.config.getoption('--programmer').upper()
    if programmer == 'CAA':
        return 'Communication Accelerator Adaptor'
    elif programmer == 'DSP3':
        return 'DSP3'
    elif programmer == 'PROMIRA':
        return 'Promira'

    raise ValueError(f"Unknown programmer: {programmer}")

@pytest.fixture(scope="session")
def side(sd, request):
    side = request.config.getoption('--side').upper()
    if side == 'LEFT':
        return sd.kLeft
    if side == 'RIGHT':
        return sd.kRight

    raise ValueError(f"Unknown side: {side}")

@pytest.fixture(scope="session")
def verify_nvm_writes(request):
    return request.config.getoption('--verify-nvm-writes')

@pytest.fixture(scope="session")
def interface_options(request):
    return request.config.getoption('--interface-options')

@pytest.fixture
def communication_interface(product_manager, programmer, side, interface_options, verify_nvm_writes):
    interface = product_manager.CreateCommunicationInterface(programmer, side, '' if interface_options is None else interface_options)
    interface.VerifyNvmWrites = verify_nvm_writes
    yield interface


@pytest.fixture
def initialized_device(sd, Ezairo, communication_interface, product):
    device_info = communication_interface.DetectDevice()
    assert device_info is not None
    assert device_info.IsValid
    assert product.InitializeDevice(communication_interface)
    yield Ezairo(sd, communication_interface, device_info, product)
    product.CloseDevice()

@pytest.fixture
def configured_device(sd, Ezairo, communication_interface, product, product_name):
    device_info = communication_interface.DetectDevice()
    assert device_info is not None
    assert device_info.IsValid
    assert device_info.FirmwareId == product_name

    if not product.InitializeDevice(communication_interface):
        product.ConfigureDevice()

    assert device_info.LibraryId == product.Definition.LibraryId
    assert device_info.ProductId == product.Definition.ProductId

    yield Ezairo(sd, communication_interface, device_info, product)
    product.CloseDevice()
