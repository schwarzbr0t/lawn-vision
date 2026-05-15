"""Tests for the Lawn Vision calculation and care guide logic."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

for _mod in (
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.util",
    "homeassistant.util.dt",
):
    sys.modules.setdefault(_mod, MagicMock())

from custom_components.lawn_vision import coordinator as cc  # noqa: E402


def make_inputs(**overrides):
    defaults = dict(
        temperature_c=22.0,
        mean_daily_temperature_c=18.0,
        soil_temperature_c=14.0,
        humidity_pct=55.0,
        moisture_pct=42.0,
        moisture_10cm_m3m3=None,
        moisture_20cm_m3m3=None,
        moisture_30cm_m3m3=None,
        rain_mm=0.0,
        grassland_temperature_sum=None,
        growing_degree_days=None,
        condition="sunny",
        grass_type="cool_season",
        area_m2=150.0,
    )
    defaults.update(overrides)
    return cc.LawnInputs(**defaults)


def make_forecast(rain_mm=0.0, rain_prob=10, hours=72, days=14, day_temp=22, day_low=12):
    hourly = [
        {
            "datetime": (datetime(2026, 5, 15, tzinfo=timezone.utc) + timedelta(hours=h)).isoformat(),
            "temperature": 19,
            "precipitation": rain_mm,
            "precipitation_probability": rain_prob,
            "condition": "sunny" if rain_prob < 50 else "rainy",
        }
        for h in range(hours)
    ]
    daily = [
        {
            "temperature": day_temp,
            "templow": day_low,
            "precipitation": rain_mm * 4,
            "precipitation_probability": rain_prob,
        }
        for _ in range(days)
    ]
    return {"hourly": hourly, "daily": daily}


NOW_MAY = datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc)
NOW_JAN = datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc)
NOW_JUL = datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)


class TestPureHelpers(unittest.TestCase):
    def test_growth_score_cool_optimum(self):
        score = cc._growth_score(21, "cool_season")
        self.assertGreater(score, 99)

    def test_growth_score_warm_optimum(self):
        score = cc._growth_score(29, "warm_season")
        self.assertGreater(score, 99)

    def test_growth_score_freezing(self):
        self.assertEqual(cc._growth_score(2, "cool_season"), 0)

    def test_growth_score_none(self):
        self.assertEqual(cc._growth_score(None, "cool_season"), 0)

    def test_phase_dormant_cold(self):
        self.assertEqual(cc._phase(0, 0, 3, 50), "dormant")

    def test_phase_stress(self):
        self.assertEqual(cc._phase(80, 70, 25, 30), "stress")

    def test_phase_dry(self):
        self.assertEqual(cc._phase(40, 20, 22, 18), "dry")

    def test_phase_active_growth(self):
        self.assertEqual(cc._phase(80, 10, 20, 45), "active_growth")

    def test_water_need_uses_moisture(self):
        self.assertGreater(cc._water_need_mm(25, 18, 0, 50), 0)

    def test_water_need_clamps_with_rain(self):
        self.assertEqual(cc._water_need_mm(30, 45, 12, 60), 0)

    def test_in_window_basic(self):
        self.assertTrue(cc._in_window(5, ((4, 5),)))
        self.assertFalse(cc._in_window(7, ((4, 5),)))

    def test_next_window_label_same_year(self):
        self.assertEqual(cc._next_window_label(3, ((4, 5),)), "April")

    def test_next_window_label_next_year(self):
        self.assertIn("naechstes Jahr", cc._next_window_label(10, ((4, 5),)))

    def test_days_since_state_none(self):
        self.assertIsNone(cc._days_since_state(None, NOW_MAY))

    def test_days_since_state_invalid(self):
        self.assertIsNone(cc._days_since_state("not-a-date", NOW_MAY))

    def test_days_since_state_iso_date(self):
        result = cc._days_since_state("2026-05-05", NOW_MAY)
        self.assertEqual(result, 10)

    def test_days_since_state_iso_datetime(self):
        result = cc._days_since_state("2026-05-13 14:00:00", NOW_MAY)
        self.assertEqual(result, 2)

    def test_days_since_state_future(self):
        result = cc._days_since_state("2026-06-01", NOW_MAY)
        self.assertEqual(result, 0)


class TestActionHeuristics(unittest.TestCase):
    def test_mow_skip_when_dormant(self):
        r = cc._action_mow(0, 20, 0, "dormant", 0, 0, None, [])
        self.assertEqual(r["state"], "skip")

    def test_mow_skip_high_stress(self):
        r = cc._action_mow(70, 70, 80, "active_growth", 10, 0, None, [])
        self.assertEqual(r["state"], "skip")

    def test_mow_wait_recent_mow(self):
        r = cc._action_mow(70, 80, 10, "active_growth", 10, 0, 1, [])
        self.assertEqual(r["state"], "wait")
        self.assertIn("Tag", r["reason"])

    def test_mow_do_now(self):
        r = cc._action_mow(70, 80, 10, "active_growth", 10, 0, 7, [])
        self.assertEqual(r["state"], "do_now")

    def test_water_skip_dormant(self):
        r = cc._action_water(10, "dormant", 0, 0, None)
        self.assertEqual(r["state"], "skip")

    def test_water_wait_on_rain(self):
        r = cc._action_water(4, "active_growth", 8, 50, None)
        self.assertEqual(r["state"], "wait")

    def test_water_do_now(self):
        r = cc._action_water(8, "active_growth", 0, 20, None)
        self.assertEqual(r["state"], "do_now")

    def test_fertilize_off_season(self):
        windows = cc.SEASONAL_WINDOWS_COOL
        r = cc._action_fertilize("waking_up", 12, 0, 1, windows, None)
        self.assertEqual(r["state"], "off_season")

    def test_fertilize_wait_cooldown(self):
        windows = cc.SEASONAL_WINDOWS_COOL
        r = cc._action_fertilize("active_growth", 12, 0, 5, windows, 10)
        self.assertEqual(r["state"], "wait")

    def test_fertilize_skip_stress(self):
        windows = cc.SEASONAL_WINDOWS_COOL
        r = cc._action_fertilize("active_growth", 12, 70, 5, windows, None)
        self.assertEqual(r["state"], "skip")

    def test_fertilize_do_now(self):
        windows = cc.SEASONAL_WINDOWS_COOL
        r = cc._action_fertilize("active_growth", 12, 0, 5, windows, 60)
        self.assertEqual(r["state"], "do_now")

    def test_scarify_off_season_summer(self):
        windows = cc.SEASONAL_WINDOWS_COOL
        r = cc._action_scarify(80, 18, "active_growth", 0, 7, windows, 0, 0, None)
        self.assertEqual(r["state"], "off_season")

    def test_scarify_wait_wet_soil(self):
        windows = cc.SEASONAL_WINDOWS_COOL
        r = cc._action_scarify(80, 12, "active_growth", 0, 5, windows, 5, 60, 200)
        self.assertEqual(r["state"], "wait")

    def test_scarify_do_now(self):
        windows = cc.SEASONAL_WINDOWS_COOL
        r = cc._action_scarify(80, 12, "active_growth", 0, 5, windows, 0, 10, 200)
        self.assertEqual(r["state"], "do_now")

    def test_overseed_extreme_forecast_blocks(self):
        windows = cc.SEASONAL_WINDOWS_COOL
        daily = [{"temperature": 33, "templow": 20, "precipitation": 0}] * 7
        r = cc._action_overseed(15, 0, 5, windows, daily, 90)
        self.assertEqual(r["state"], "wait")

    def test_overseed_do_now(self):
        windows = cc.SEASONAL_WINDOWS_COOL
        daily = [{"temperature": 22, "templow": 12, "precipitation": 0}] * 7
        r = cc._action_overseed(14, 0, 5, windows, daily, 90)
        self.assertEqual(r["state"], "do_now")


class TestConflictResolver(unittest.TestCase):
    def test_annual_action_capped_when_no_tracking(self):
        actions = {
            cc.ACTION_MOW: {"state": "wait", "next_window": "", "reason": "", "days_since": None, "cooldown_days": 7},
            cc.ACTION_WATER: {"state": "wait", "next_window": "", "reason": "", "days_since": None, "cooldown_days": 3},
            cc.ACTION_FERTILIZE: {"state": "wait", "next_window": "", "reason": "", "days_since": None, "cooldown_days": 42},
            cc.ACTION_SCARIFY: {"state": "do_now", "next_window": "Heute", "reason": "x", "days_since": None, "cooldown_days": 180},
            cc.ACTION_AERATE: {"state": "do_now", "next_window": "Heute", "reason": "y", "days_since": None, "cooldown_days": 300},
            cc.ACTION_OVERSEED: {"state": "do_now", "next_window": "Diese Woche", "reason": "z", "days_since": None, "cooldown_days": 60},
        }
        result = cc._resolve_conflicts(dict(actions), {k: None for k in actions})
        for action in (cc.ACTION_SCARIFY, cc.ACTION_AERATE, cc.ACTION_OVERSEED):
            self.assertEqual(result[action]["state"], "soon")
            self.assertIn("input_datetime", result[action]["reason"])

    def test_scarify_downgrades_fertilize_and_aerate(self):
        actions = {
            cc.ACTION_MOW: {"state": "wait", "next_window": "", "reason": "", "days_since": None, "cooldown_days": 7},
            cc.ACTION_WATER: {"state": "wait", "next_window": "", "reason": "", "days_since": None, "cooldown_days": 3},
            cc.ACTION_FERTILIZE: {"state": "do_now", "next_window": "Heute", "reason": "ok", "days_since": 50, "cooldown_days": 42},
            cc.ACTION_SCARIFY: {"state": "do_now", "next_window": "Heute", "reason": "x", "days_since": 200, "cooldown_days": 180},
            cc.ACTION_AERATE: {"state": "do_now", "next_window": "Heute", "reason": "y", "days_since": 320, "cooldown_days": 300},
            cc.ACTION_OVERSEED: {"state": "wait", "next_window": "", "reason": "", "days_since": 30, "cooldown_days": 60},
        }
        last_done = {k: "2025-05-01" for k in actions}
        result = cc._resolve_conflicts(dict(actions), last_done)
        self.assertEqual(result[cc.ACTION_SCARIFY]["state"], "do_now")
        self.assertEqual(result[cc.ACTION_FERTILIZE]["state"], "soon")
        self.assertIn("vertikutieren", result[cc.ACTION_FERTILIZE]["reason"].lower())
        self.assertEqual(result[cc.ACTION_AERATE]["state"], "soon")

    def test_overseed_plus_fertilize_adds_starter_hint(self):
        actions = {
            cc.ACTION_MOW: {"state": "wait", "next_window": "", "reason": "", "days_since": None, "cooldown_days": 7},
            cc.ACTION_WATER: {"state": "wait", "next_window": "", "reason": "", "days_since": None, "cooldown_days": 3},
            cc.ACTION_FERTILIZE: {"state": "do_now", "next_window": "Heute", "reason": "base", "days_since": 50, "cooldown_days": 42},
            cc.ACTION_SCARIFY: {"state": "wait", "next_window": "", "reason": "", "days_since": 30, "cooldown_days": 180},
            cc.ACTION_AERATE: {"state": "wait", "next_window": "", "reason": "", "days_since": 30, "cooldown_days": 300},
            cc.ACTION_OVERSEED: {"state": "do_now", "next_window": "Diese Woche", "reason": "go", "days_since": 100, "cooldown_days": 60},
        }
        last_done = {k: "2025-05-01" for k in actions}
        result = cc._resolve_conflicts(dict(actions), last_done)
        self.assertIn("Starterduenger", result[cc.ACTION_FERTILIZE]["reason"])


class TestNextAction(unittest.TestCase):
    def _actions(self, **states):
        base = {a: {"state": "wait"} for a in cc.CARE_ACTIONS}
        base.update({k: {"state": v} for k, v in states.items()})
        return base

    def test_water_wins_priority(self):
        actions = self._actions(water="do_now", mow="do_now", fertilize="do_now")
        self.assertEqual(cc._next_action(actions), "water")

    def test_mow_when_water_not_due(self):
        actions = self._actions(mow="do_now", fertilize="do_now")
        self.assertEqual(cc._next_action(actions), "mow")

    def test_falls_back_to_soon(self):
        actions = self._actions(scarify="soon", aerate="soon")
        self.assertEqual(cc._next_action(actions), "scarify")

    def test_none_when_nothing(self):
        actions = self._actions()
        self.assertEqual(cc._next_action(actions), "none")


class TestCalculateMetricsEndToEnd(unittest.TestCase):
    def test_happy_path_spring(self):
        inputs = make_inputs()
        result = cc.calculate_metrics(inputs, make_forecast(), last_done={}, now=NOW_MAY)
        self.assertIn(result["phase"], ("waking_up", "active_growth"))
        self.assertIn("actions", result)
        self.assertEqual(len(result["actions"]), 6)
        self.assertIn(result["next_action"], ("mow", "water", "fertilize", "overseed", "scarify", "aerate", "none"))
        for action in cc.CARE_ACTIONS:
            self.assertIn(result[f"action_{action}"], result["actions"].values())

    def test_winter_off_season(self):
        inputs = make_inputs(temperature_c=2, mean_daily_temperature_c=1, soil_temperature_c=3)
        result = cc.calculate_metrics(inputs, make_forecast(), last_done={}, now=NOW_JAN)
        self.assertEqual(result["phase"], "dormant")
        self.assertEqual(result["next_action"], "none")
        for annual in (cc.ACTION_SCARIFY, cc.ACTION_AERATE, cc.ACTION_OVERSEED):
            self.assertEqual(result["actions"][annual]["state"], "off_season")

    def test_heat_wave_water_wins(self):
        inputs = make_inputs(
            temperature_c=32, mean_daily_temperature_c=28, soil_temperature_c=24,
            humidity_pct=35, moisture_pct=18,
        )
        result = cc.calculate_metrics(inputs, make_forecast(), last_done={}, now=NOW_JUL)
        self.assertEqual(result["next_action"], "water")
        self.assertEqual(result["actions"][cc.ACTION_WATER]["state"], "do_now")

    def test_last_done_respected(self):
        inputs = make_inputs()
        last_done = {"fertilize": (NOW_MAY - timedelta(days=10)).date().isoformat()}
        result = cc.calculate_metrics(inputs, make_forecast(), last_done=last_done, now=NOW_MAY)
        fert = result["actions"][cc.ACTION_FERTILIZE]
        self.assertEqual(fert["state"], "wait")
        self.assertEqual(fert["days_since"], 10)


if __name__ == "__main__":
    unittest.main()
