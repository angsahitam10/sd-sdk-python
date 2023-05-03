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
        raise ImportError('Failed to find the Sound Designer SDK! Make sure you set "SD_SDK_ROOT" appropriately in your environment.')

    sdk_bin_folder = sdk_root / _WIN_SAMPLES_PATH

    if not sdk_bin_folder.exists() or not sdk_bin_folder.is_dir():
        logging.error(f"Failed to find Windows SDK module at {str(sdk_bin_folder)}")
        raise ImportError(f'Failed to find the Sound Designer SDK Windows samples folder! Make sure "%SD_SDK_ROOT%/{_WIN_SAMPLES_PATH}" exists.')

    str_sdk_bin_folder = str(sdk_bin_folder)

    # Set the SDK environment variables BEFORE attempting to import from sd
    # Note that the trailing separator is required for the SDK to work
    os.environ['SD_MODULE_PATH'] = str_sdk_bin_folder + '\\' if not str_sdk_bin_folder else ''
    os.environ['SD_CONFIG_PATH'] = str(sdk_bin_folder / 'sd.config')
    os.environ["PATH"] += os.pathsep + str_sdk_bin_folder
    sys.path.append(str_sdk_bin_folder)
    import sd
    globals()["sd"] = sd


__resolve_sdk()

__pm = sd.ProductManager()

def get_product_manager():
    return __pm

__all__ = ["sd", "get_product_manager", "sd_sdk"]
