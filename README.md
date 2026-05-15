# Lawn Vision

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

## Inputs

Required:

- A Home Assistant weather entity or a temperature sensor.

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

## Manual installation for development

Copy the integration:

```bash
cp -R custom_components/lawn_vision /config/custom_components/
```

Copy the card:

```bash
mkdir -p /config/www/community/lawn-vision
cp dist/lawn-vision.js /config/www/community/lawn-vision/lawn-vision.js
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

## HACS packaging note

This MVP keeps the integration and the dashboard card in one repository because
it is easier to iterate on the product shape. For a public HACS launch, the
cleanest route is usually one of these:

- Publish two repositories: `lawn-vision` as an integration and
  `lawn-vision-card` as a dashboard card.
- Keep this repository as a custom/manual install during early alpha testing.

The dashboard file is named `dist/lawn-vision.js` so a Dashboard-type HACS repo
named `lawn-vision` can discover it.

## Calculation model

The MVP is intentionally transparent. It estimates:

- Growth from a temperature curve with different optimums for cool-season and
  warm-season grasses.
- Mowing suitability from growth, moisture and wet-weather penalties.
- Water need from soil moisture or, if unavailable, heat and humidity pressure.
- Stress from heat, dryness and wet mowing risk.

These rules are not a replacement for agronomic measurements, but they create a
useful first decision layer for Home Assistant users.

## Roadmap

- 7 to 14 day forecast window.
- DWD/Open-Meteo source adapter.
- Mower and irrigation automation helpers.
- Lawn journal entities: last mow, last fertilize, last overseed.
- HACS-ready split packages once the API stabilizes.
