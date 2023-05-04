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
import sys
import os
import pathlib
import logging


_WIN_SAMPLES_PATH = 'samples/win/bin'

def __get_run_path():
    """Returns the directory of this script"""
    # This check is required if the script has been frozen via py2exe
    if hasattr(sys, "frozen"):
        return os.path.abspath(os.path.dirname(sys.executable))

    return os.path.abspath(os.path.dirname(__file__))


def __resolve_sdk():
    """Sets the SDK environment variables and imports the sd module"""
    sdk_root = pathlib.Path(os.environ.get('SD_SDK_ROOT', __get_run_path()))
    if not sdk_root.exists() or not sdk_root.is_dir():
        raise ImportError(f'{str(sdk_root)} is not a valid location. Make sure you set %SD_SDK_ROOT% appropriately in your environment.')

    # We'll fall back to this if we can't find sd.pyd in SD_SDK_ROOT
    sdk_module_folder = sdk_root / _WIN_SAMPLES_PATH

    # Try to find the sd.pyd file in sdk_root
    try_sd_pyd = sdk_root / 'sd.pyd'
    if try_sd_pyd.exists() and try_sd_pyd.is_file():
        logging.debug(f"Found 'sd.pyd' in {str(sdk_root)}")
        sdk_module_folder = sdk_root
    else:
        logging.debug(f"Failed to find 'sd.pyd' in {str(sdk_root)}. Using {str(sdk_module_folder)} instead.")

    sdk_module = sdk_module_folder / 'sd.pyd'
    sdk_config = sdk_module_folder / 'sd.config'

    if not sdk_module.exists() or not sdk_module.is_file():
        raise ImportError(f"Failed to find 'sd.pyd' in {str(sdk_module_folder)}! Make sure you set %SD_SDK_ROOT% appropriately in your environment.")

    # Set the SDK environment variables BEFORE attempting to import from sd
    # Note that the trailing separator is required for the SDK to work
    os.environ['SD_MODULE_PATH'] = str(sdk_module.parent) + '\\'
    os.environ['SD_CONFIG_PATH'] = str(sdk_config)
    os.environ["PATH"] += os.pathsep + str(sdk_module.parent)
    sys.path.append(str(sdk_module.parent))
    import sd
    globals()["sd"] = sd


__resolve_sdk()

__pm = sd.ProductManager()

def get_product_manager():
    return __pm

__all__ = ["sd", "get_product_manager", "sd_sdk"]
