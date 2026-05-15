"""Pytest setup: stub homeassistant imports before any test module loads them."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

_HA_MODULES = (
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.util",
    "homeassistant.util.dt",
)

for _mod in _HA_MODULES:
    sys.modules.setdefault(_mod, MagicMock())
