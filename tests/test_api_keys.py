import os
import pytest

from utils.api_keys import APIKeyManager


def test_api_key_rotation():
    os.environ['OPENAI_API_KEYS'] = 'key1,key2'
    manager = APIKeyManager()

    key_a = manager.acquire()
    key_b = manager.acquire()

    assert key_a.endswith('key1') or key_a.endswith('key2')
    assert key_b.endswith('key1') or key_b.endswith('key2')
    assert key_a != key_b

    manager.report_failure(key_a)
    manager.report_failure(key_a)
    manager.report_failure(key_a)

    assert manager.acquire() != key_a


def test_api_key_reset():
    os.environ['OPENAI_API_KEYS'] = 'one'
    manager = APIKeyManager()
    key = manager.acquire()
    manager.report_failure(key)
    manager.reset()
    assert manager.acquire() == key
