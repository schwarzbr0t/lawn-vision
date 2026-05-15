"""Constants for Lawn Vision."""

from __future__ import annotations

DOMAIN = "lawn_vision"
DEFAULT_NAME = "Lawn Vision"

CONF_AREA_M2 = "area_m2"
CONF_GRASS_TYPE = "grass_type"
CONF_GDD_ENTITY = "gdd_entity"
CONF_GTS_ENTITY = "grassland_temperature_sum_entity"
CONF_HUMIDITY_ENTITY = "humidity_entity"
CONF_MEAN_DAILY_TEMPERATURE_ENTITY = "mean_daily_temperature_entity"
CONF_MOISTURE_ENTITY = "moisture_entity"
CONF_MOISTURE_10CM_ENTITY = "moisture_10cm_entity"
CONF_MOISTURE_20CM_ENTITY = "moisture_20cm_entity"
CONF_MOISTURE_30CM_ENTITY = "moisture_30cm_entity"
CONF_RAIN_ENTITY = "rain_entity"
CONF_SOIL_TEMPERATURE_ENTITY = "soil_temperature_entity"
CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_WEATHER_ENTITY = "weather_entity"

GRASS_COOL_SEASON = "cool_season"
GRASS_WARM_SEASON = "warm_season"
GRASS_TYPES = [GRASS_COOL_SEASON, GRASS_WARM_SEASON]

DEFAULT_AREA_M2 = 150
DEFAULT_GRASS_TYPE = GRASS_COOL_SEASON

SENSOR_PHASE = "phase"
SENSOR_GROWTH_SCORE = "growth_score"
SENSOR_FORECAST_BEST_WINDOW = "forecast_best_window"
SENSOR_FORECAST_CARE_HINT = "forecast_care_hint"
SENSOR_FORECAST_GROWTH_TREND = "forecast_growth_trend"
SENSOR_FORECAST_RAIN_RISK = "forecast_rain_risk"
SENSOR_FORECAST_WATER_NEED = "forecast_water_need"
SENSOR_GROWING_DEGREE_DAYS = "growing_degree_days"
SENSOR_GRASSLAND_TEMPERATURE_SUM = "grassland_temperature_sum"
SENSOR_MEAN_DAILY_TEMPERATURE = "mean_daily_temperature"
SENSOR_MOWING_CONDITION = "mowing_condition"
SENSOR_MOISTURE_10CM = "moisture_10cm"
SENSOR_MOISTURE_20CM = "moisture_20cm"
SENSOR_MOISTURE_30CM = "moisture_30cm"
SENSOR_WATER_NEED = "water_need"
SENSOR_SOIL_TEMPERATURE = "soil_temperature"
SENSOR_STRESS_LEVEL = "stress_level"
SENSOR_RECOMMENDATION = "recommendation"
