import pytest


def test_import_sdk_module(sd):
    assert sd.kRSL10 == 2


def test_product_manager(sd, product_manager):
    assert type(product_manager) == sd.ProductManager


def test_product_memories(product):
    assert len(product.Memories) == 8
