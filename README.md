<p align="center">
  <img src="custom_components/lawn_vision/brand/icon.png" alt="Lawn Vision" width="160" />
</p>

# Lawn Vision

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/v/release/schwarzbr0t/lawn-vision)](https://github.com/schwarzbr0t/lawn-vision/releases)
[![HACS Action](https://github.com/schwarzbr0t/lawn-vision/actions/workflows/tests.yml/badge.svg)](https://github.com/schwarzbr0t/lawn-vision/actions/workflows/tests.yml)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-kevinschwarz-ffdd00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/kevinschwarz)

Lawn Vision is a Home Assistant MVP for a more visual, decision-oriented lawn
dashboard. It turns existing weather and garden entities into simple care
signals: growth phase, growth score, mowing window, water need, stress level
and a plain-language recommendation.

![Lawn Vision preview](docs/preview.svg)

## What it does

- Calculates a local lawn growth score from temperature and grass type.
- Uses optional soil moisture, rain and humidity entities to refine care advice.
- Exposes Home Assistant sensors for automations and dashboards.
- Adds a custom Lovelace card that feels native to Home Assistant themes.
- Works without cloud accounts or API keys in the MVP.

## Sensors

The integration creates these sensors:

- `sensor.lawn_vision_phase`
- `sensor.lawn_vision_growth_score`
- `sensor.lawn_vision_soil_temperature`
- `sensor.lawn_vision_mean_daily_temperature`
- `sensor.lawn_vision_grassland_temperature_sum`
- `sensor.lawn_vision_growing_degree_days`
- `sensor.lawn_vision_moisture_10cm`
- `sensor.lawn_vision_moisture_20cm`
- `sensor.lawn_vision_moisture_30cm`
- `sensor.lawn_vision_mowing_condition`
- `sensor.lawn_vision_water_need`
- `sensor.lawn_vision_stress_level`
- `sensor.lawn_vision_recommendation`
- `sensor.lawn_vision_forecast_rain_risk`
- `sensor.lawn_vision_forecast_water_need`
- `sensor.lawn_vision_forecast_growth_trend`
- `sensor.lawn_vision_forecast_best_window`
- `sensor.lawn_vision_forecast_care_hint`

Care guide sensors (each exposes a state plus `reason`, `next_window`,
`days_since`, `cooldown_days` attributes):

- `sensor.lawn_vision_action_mow`
- `sensor.lawn_vision_action_water`
- `sensor.lawn_vision_action_fertilize`
- `sensor.lawn_vision_action_scarify`
- `sensor.lawn_vision_action_aerate`
- `sensor.lawn_vision_action_overseed`
- `sensor.lawn_vision_next_action` – headline action for today

Action states are `do_now`, `soon`, `wait`, `skip`, `off_season`. The
`next_action` sensor returns the recommended action id (`mow`, `water`,
`fertilize`, `scarify`, `aerate`, `overseed`, or `none`).

## Inputs

Required:

- A Home Assistant weather entity, a temperature sensor, **or** the
  built-in [Open-Meteo](https://open-meteo.com/) adapter (no API key
  required, attribution: weather data by Open-Meteo).

Optional but recommended:

- Humidity sensor
- Soil moisture sensor
- Soil temperature sensor
- Mean daily temperature sensor
- Grassland temperature sum sensor
- Growing Degree Days sensor
- Soil moisture sensors for 10 cm, 20 cm and 30 cm depth
- Rain sensor
- Lawn area
- Grass type: cool-season or warm-season lawn

For the care guide, the integration ships native `date` entities that
track when each task was last performed:

- `date.lawn_vision_last_mow`
- `date.lawn_vision_last_water`
- `date.lawn_vision_last_fertilize`
- `date.lawn_vision_last_scarify`
- `date.lawn_vision_last_aerate`
- `date.lawn_vision_last_overseed`

Update them from the UI or via the `date.set_value` service. The values
persist across restarts. If you prefer an `input_datetime` helper, set
its entity id in the options flow and it takes precedence over the
native journal entity.

## Manual installation for development

Copy the integration:

```bash
cp -R custom_components/lawn_vision /config/custom_components/
```

The dashboard card lives in a separate repository:
[schwarzbr0t/lawn-vision-card](https://github.com/schwarzbr0t/lawn-vision-card).
For manual install, follow its README; in short:

```bash
mkdir -p /config/www/community/lawn-vision
curl -L -o /config/www/community/lawn-vision/lawn-vision.js \
  https://raw.githubusercontent.com/schwarzbr0t/lawn-vision-card/main/dist/lawn-vision.js
cp docs/rasen.png /config/www/community/lawn-vision/rasen.png
```

Add the Lovelace resource:

```yaml
url: /local/community/lawn-vision/lawn-vision.js
type: module
```

Then restart Home Assistant, add the Lawn Vision integration, and add a manual
dashboard card:

```yaml
type: custom:lawn-vision-card
title: Lawn Vision
background_image: /local/community/lawn-vision/rasen.png
background_position: center
background_size: cover
layout: auto
size: normal
show_agro: true
show_forecast: true
show_timeline: true
show_recommendation: true
show_care_guide: true
visual:
  density: normal
  accent_color: "#42d65d"
  water_color: "#46a2ff"
  warning_color: "#f4b72f"
  card_radius: 16
  section_radius: 12
  overlay_opacity: 0.78
  vignette_opacity: 0.16
  panel_opacity: 0.76
  blur: 16
  text_scale: 1
  min_height: 0
entity_phase: sensor.lawn_vision_phase
entity_growth: sensor.lawn_vision_growth_score
entity_soil_temperature: sensor.lawn_vision_soil_temperature
entity_mean_daily_temperature: sensor.lawn_vision_mean_daily_temperature
entity_grassland_temperature_sum: sensor.lawn_vision_grassland_temperature_sum
entity_growing_degree_days: sensor.lawn_vision_growing_degree_days
entity_moisture_10cm: sensor.lawn_vision_moisture_10cm
entity_moisture_20cm: sensor.lawn_vision_moisture_20cm
entity_moisture_30cm: sensor.lawn_vision_moisture_30cm
entity_mowing: sensor.lawn_vision_mowing_condition
entity_water: sensor.lawn_vision_water_need
entity_stress: sensor.lawn_vision_stress_level
entity_recommendation: sensor.lawn_vision_recommendation
entity_forecast_rain_risk: sensor.lawn_vision_forecast_rain_risk
entity_forecast_water_need: sensor.lawn_vision_forecast_water_need
entity_forecast_growth_trend: sensor.lawn_vision_forecast_growth_trend
entity_forecast_best_window: sensor.lawn_vision_forecast_best_window
entity_forecast_care_hint: sensor.lawn_vision_forecast_care_hint
entity_action_mow: sensor.lawn_vision_action_mow
entity_action_water: sensor.lawn_vision_action_water
entity_action_fertilize: sensor.lawn_vision_action_fertilize
entity_action_scarify: sensor.lawn_vision_action_scarify
entity_action_aerate: sensor.lawn_vision_action_aerate
entity_action_overseed: sensor.lawn_vision_action_overseed
entity_next_action: sensor.lawn_vision_next_action
```

For narrow dashboard columns, use the compact mode:

```yaml
layout: compact
size: compact
show_agro: true
show_timeline: true
show_recommendation: false
visual:
  density: dense
  text_scale: 0.9
  panel_opacity: 0.82
```

For a flatter Home Assistant tile style:

```yaml
background_image: ""
visual:
  density: dense
  accent_color: "#8bc34a"
  card_radius: 12
  section_radius: 8
  overlay_opacity: 1
  panel_opacity: 0.58
  blur: 0
  text_scale: 0.92
```

Advanced visual overrides can set CSS variables directly:

```yaml
visual:
  css_variables:
    lv-title: 24px
    lv-ring: 88px
    lv-plan-value: 17px
```

The card also provides a visual editor in the Home Assistant dashboard card
dialog. Open the card, switch to the visual editor, and adjust layout, sections,
colors, opacity, blur, radii and text scale without editing YAML by hand.

## HACS packaging

This repository is a **HACS custom integration**: add it as an
*Integration* custom repository in HACS and it will install the
`lawn_vision` integration from `custom_components/`.

The Lovelace dashboard card has its own repository:
[schwarzbr0t/lawn-vision-card](https://github.com/schwarzbr0t/lawn-vision-card).
Add that one as a *Lovelace plugin* custom repository in HACS to
install the dashboard card.

## Calculation model

The MVP is intentionally transparent. It estimates:

- Growth from a temperature curve with different optimums for cool-season and
  warm-season grasses.
- Mowing suitability from growth, moisture and wet-weather penalties.
- Water need from soil moisture or, if unavailable, heat and humidity pressure.
- Stress from heat, dryness and wet mowing risk.

These rules are not a replacement for agronomic measurements, but they create a
useful first decision layer for Home Assistant users.

## Example automations

See [examples/automations.yaml](examples/automations.yaml) for ready-made
automations that:

- Notify when the headline care action changes
- Log the last mow when a robot mower returns to its dock
- Run irrigation when the water action turns `do_now` and rain risk is low
- Send a fertilize reminder when the window opens
- Pause the mower under high stress

## Roadmap

- 7 to 14 day forecast window with per-day care plan.
- DWD/Open-Meteo source adapter for users without a weather entity.
- Lawn journal entities exposed as native sensors (currently
  `input_datetime` helpers are wired in via the options flow).
- HACS-ready split packages once the API stabilizes.
