"""Tests for config entry migration."""

from unittest.mock import MagicMock

import pytest

from custom_components.wx_watcher.const import (
    CONF_INTERVAL,
    CONF_TIMEOUT,
    CONFIG_VERSION,
    DEFAULT_TIMEOUT,
    MAX_TIMEOUT,
)
from custom_components.wx_watcher.migration import async_migrate_entry

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_update_entry(hass):
    """Mock async_update_entry and restore after test."""
    original = hass.config_entries.async_update_entry

    def _update(config_entry, **kwargs):
        if "data" in kwargs:
            config_entry.data = kwargs["data"]
        if "version" in kwargs:
            config_entry.version = kwargs["version"]

    hass.config_entries.async_update_entry = _update
    yield
    hass.config_entries.async_update_entry = original


def _make_entry(hass, version: int, data: dict):
    """Create a mock config entry."""
    entry = MagicMock()
    entry.version = version
    entry.data = dict(data)
    return entry


async def test_migration_v4_to_v5_default_values(hass, mock_update_entry):
    """Test v4→v5 migration with old defaults (interval=1min, timeout=120s)."""
    entry = _make_entry(hass, version=4, data={CONF_INTERVAL: 1, CONF_TIMEOUT: 120})
    result = await async_migrate_entry(hass, entry)
    assert result is True
    assert entry.version == CONFIG_VERSION
    assert entry.data[CONF_INTERVAL] == 60
    assert entry.data[CONF_TIMEOUT] == DEFAULT_TIMEOUT


async def test_migration_v4_to_v5_custom_interval(hass, mock_update_entry):
    """Test v4→v5 migration with custom interval (2 minutes)."""
    entry = _make_entry(hass, version=4, data={CONF_INTERVAL: 2, CONF_TIMEOUT: 120})
    result = await async_migrate_entry(hass, entry)
    assert result is True
    assert entry.data[CONF_INTERVAL] == 120
    assert entry.data[CONF_TIMEOUT] == DEFAULT_TIMEOUT


async def test_migration_v4_to_v5_custom_timeout(hass, mock_update_entry):
    """Test v4→v5 migration with custom timeout — preserved if within bounds."""
    entry = _make_entry(hass, version=4, data={CONF_INTERVAL: 1, CONF_TIMEOUT: 60})
    result = await async_migrate_entry(hass, entry)
    assert result is True
    assert entry.data[CONF_INTERVAL] == 60
    assert entry.data[CONF_TIMEOUT] == 60


async def test_migration_v4_to_v5_timeout_over_max(hass, mock_update_entry):
    """Test v4→v5 migration caps timeout exceeding MAX_TIMEOUT."""
    entry = _make_entry(hass, version=4, data={CONF_INTERVAL: 1, CONF_TIMEOUT: 200})
    result = await async_migrate_entry(hass, entry)
    assert result is True
    assert entry.data[CONF_TIMEOUT] == MAX_TIMEOUT


async def test_migration_v4_to_v5_missing_timeout(hass, mock_update_entry):
    """Test v4→v5 migration when timeout key is missing (defaults to 120→DEFAULT_TIMEOUT)."""
    entry = _make_entry(hass, version=4, data={CONF_INTERVAL: 3})
    result = await async_migrate_entry(hass, entry)
    assert result is True
    assert entry.data[CONF_INTERVAL] == 180
    assert entry.data[CONF_TIMEOUT] == DEFAULT_TIMEOUT


async def test_migration_v4_to_v5_missing_interval(hass, mock_update_entry):
    """Test v4→v5 migration when interval key is missing (defaults to 1min→60s)."""
    entry = _make_entry(hass, version=4, data={CONF_TIMEOUT: 120})
    result = await async_migrate_entry(hass, entry)
    assert result is True
    assert entry.data[CONF_INTERVAL] == 60
    assert entry.data[CONF_TIMEOUT] == DEFAULT_TIMEOUT
