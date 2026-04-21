"""Tests for number entity bounds validation."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.wx_watcher.const import (
    CONF_INTERVAL,
    CONF_TIMEOUT,
    DEFAULT_INTERVAL,
    DEFAULT_TIMEOUT,
    MAX_INTERVAL,
    MAX_TIMEOUT,
    MIN_INTERVAL,
    MIN_TIMEOUT,
)
from custom_components.wx_watcher.number import WXWatcherIntervalNumber, WXWatcherTimeoutNumber

pytestmark = pytest.mark.asyncio


def _make_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.update_interval = timedelta(seconds=DEFAULT_INTERVAL)
    coordinator.timeout = DEFAULT_TIMEOUT
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


def _make_entry(data: dict | None = None):
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = data or {CONF_INTERVAL: DEFAULT_INTERVAL, CONF_TIMEOUT: DEFAULT_TIMEOUT}
    return entry


async def test_interval_clamps_below_min():
    """Setting interval below MIN_INTERVAL should clamp to MIN_INTERVAL."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    entity = WXWatcherIntervalNumber(coordinator, entry)
    entity.hass = MagicMock()

    with patch.object(entity, "async_write_ha_state"):
        await entity.async_set_native_value(float(MIN_INTERVAL - 10))
    assert entity.native_value == float(MIN_INTERVAL)


async def test_interval_clamps_above_max():
    """Setting interval above MAX_INTERVAL should clamp to MAX_INTERVAL."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    entity = WXWatcherIntervalNumber(coordinator, entry)
    entity.hass = MagicMock()

    with patch.object(entity, "async_write_ha_state"):
        await entity.async_set_native_value(float(MAX_INTERVAL + 100))
    assert entity.native_value == float(MAX_INTERVAL)


async def test_interval_within_bounds_unchanged():
    """Setting interval within bounds should not clamp."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    entity = WXWatcherIntervalNumber(coordinator, entry)
    entity.hass = MagicMock()

    with patch.object(entity, "async_write_ha_state"):
        await entity.async_set_native_value(60.0)
    assert entity.native_value == 60.0


async def test_timeout_clamps_below_min():
    """Setting timeout below MIN_TIMEOUT should clamp to MIN_TIMEOUT."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    entity = WXWatcherTimeoutNumber(coordinator, entry)
    entity.hass = MagicMock()

    with patch.object(entity, "async_write_ha_state"):
        await entity.async_set_native_value(float(MIN_TIMEOUT - 5))
    assert entity.native_value == float(MIN_TIMEOUT)


async def test_timeout_clamps_above_max():
    """Setting timeout above MAX_TIMEOUT should clamp to MAX_TIMEOUT."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    entity = WXWatcherTimeoutNumber(coordinator, entry)
    entity.hass = MagicMock()

    with patch.object(entity, "async_write_ha_state"):
        await entity.async_set_native_value(float(MAX_TIMEOUT + 50))
    assert entity.native_value == float(MAX_TIMEOUT)


async def test_timeout_within_bounds_unchanged():
    """Setting timeout within bounds should not clamp."""
    coordinator = _make_coordinator()
    entry = _make_entry()
    entity = WXWatcherTimeoutNumber(coordinator, entry)
    entity.hass = MagicMock()

    with patch.object(entity, "async_write_ha_state"):
        await entity.async_set_native_value(45.0)
    assert entity.native_value == 45.0
