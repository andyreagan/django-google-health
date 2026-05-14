> Fetched 2026-05-14 from https://developers.google.com/health/data-types

# Google Health API Data Types

## Overview

The Google Health API provides a comprehensive set of data types for health and fitness tracking. This documentation details all available data types, their representations, available operations, required scopes, and webhook support.

**Important**: Data type identifiers use different formats depending on context. In endpoints, use kebab case (e.g., `body-fat`). In filter parameters, use snake case (e.g., `body_fat`).

## Data Types Table

| Data Type | `dataType` | `filter` Parameter | Record Type | Available Operations | Scope | Webhook Support |
|-----------|-----------|-------------------|-------------|----------------------|-------|-----------------|
| [Active Minutes](/health/reference/rest/v4/users.dataTypes.dataPoints#activeminutes) | `active-minutes` | `active_minutes` | Interval | reconcile, rollup, dailyRollup | activity_and_fitness | |
| [Active Zone Minutes](/health/reference/rest/v4/users.dataTypes.dataPoints#activezoneminutes) | `active-zone-minutes` | `active_zone_minutes` | Interval | list, reconcile, rollup, dailyRollup | activity_and_fitness | |
| [Activity Level](/health/reference/rest/v4/users.dataTypes.dataPoints#activitylevel) | `activity-level` | `activity_level` | Interval | list, reconcile | activity_and_fitness | |
| [Altitude](/health/reference/rest/v4/users.dataTypes.dataPoints#altitude) | `altitude` | `altitude` | Interval | list, reconcile, rollup, dailyRollup | activity_and_fitness | |
| [Body Fat](/health/reference/rest/v4/users.dataTypes.dataPoints#bodyfat) | `body-fat` | `body_fat` | Sample | list, get, reconcile, rollup, dailyRollup, create, update, batchDelete | health_metrics_and_measurements | |
| [Calories In Heart Rate Zone](/health/reference/rest/v4/users.dataTypes.dataPoints#caloriesinheartratezone) | `calories-in-heart-rate-zone` | `calories_in_heart_rate_zone` | Interval | rollup, dailyRollup | activity_and_fitness | |
| [Daily Heart Rate Variability](/health/reference/rest/v4/users.dataTypes.dataPoints#dailyheartratevariability) | `daily-heart-rate-variability` | `daily_heart_rate_variability` | Daily | list, reconcile | health_metrics_and_measurements | |
| [Daily Heart Rate Zones](/health/reference/rest/v4/users.dataTypes.dataPoints#dailyheartratezones) | `daily-heart-rate-zones` | `daily_heart_rate_zones` | Daily | reconcile | health_metrics_and_measurements | |
| [Daily Oxygen Saturation](/health/reference/rest/v4/users.dataTypes.dataPoints#dailyoxygensaturation) | `daily-oxygen-saturation` | `daily_oxygen_saturation` | Daily | list, reconcile | health_metrics_and_measurements | |
| [Daily Respiratory Rate](/health/reference/rest/v4/users.dataTypes.dataPoints#dailyrespiratoryrate) | `daily-respiratory-rate` | `daily_respiratory_rate` | Daily | list, reconcile | health_metrics_and_measurements | |
| [Daily Resting Heart Rate](/health/reference/rest/v4/users.dataTypes.dataPoints#dailyrestingheartrate) | `daily-resting-heart-rate` | `daily_resting_heart_rate` | Daily | list, reconcile | health_metrics_and_measurements | |
| [Daily Sleep Temperature Derivations](/health/reference/rest/v4/users.dataTypes.dataPoints#dailysleeptemperaturederivations) | `daily-sleep-temperature-derivations` | `daily_sleep_temperature_derivations` | Daily | list, reconcile | health_metrics_and_measurements | |
| [Daily VO2 Max](/health/reference/rest/v4/users.dataTypes.dataPoints#dailyvo2max) | `daily-vo2-max` | `daily_vo2_max` | Daily | list, reconcile | activity_and_fitness | |
| [Distance](/health/reference/rest/v4/users.dataTypes.dataPoints#distance) | `distance` | `distance` | Interval | list, reconcile, rollup, dailyRollup | activity_and_fitness | |
| [Exercise](/health/reference/rest/v4/users.dataTypes.dataPoints#exercise) | `exercise` | `exercise` | Session | list, get, reconcile, create, update, batchDelete | activity_and_fitness | |
| [Floors](/health/reference/rest/v4/users.dataTypes.dataPoints#floors) | `floors` | `floors` | Interval | reconcile, rollup, dailyRollup | activity_and_fitness | |
| [Heart Rate](/health/reference/rest/v4/users.dataTypes.dataPoints#heartrate) | `heart-rate` | `heart_rate` | Sample | list, reconcile, rollup, dailyRollup | health_metrics_and_measurements | |
| [Heart Rate Variability](/health/reference/rest/v4/users.dataTypes.dataPoints#heartratevariability) | `heart-rate-variability` | `heart_rate_variability` | Sample | list, reconcile | health_metrics_and_measurements | |
| [Height](/health/reference/rest/v4/users.dataTypes.dataPoints#height) | `height` | `height` | Sample | list, get, reconcile, create, update, batchDelete | health_metrics_and_measurements | |
| [Hydration Log](/health/reference/rest/v4/users.dataTypes.dataPoints#hydrationlog) | `hydration-log` | `hydration_log` | Session | list, get, reconcile, rollup, dailyRollup, create, update, batchDelete | nutrition | |
| [Oxygen Saturation](/health/reference/rest/v4/users.dataTypes.dataPoints#oxygensaturation) | `oxygen-saturation` | `oxygen_saturation` | Sample | list, reconcile | health_metrics_and_measurements | |
| [Respiratory Rate Sleep Summary](/health/reference/rest/v4/users.dataTypes.dataPoints#respiratoryratesleepsummary) | `respiratory-rate-sleep-summary` | `respiratory_rate_sleep_summary` | Sample | list, reconcile | health_metrics_and_measurements | |
| [Run VO2 Max](/health/reference/rest/v4/users.dataTypes.dataPoints#runvo2max) | `run-vo2-max` | `run_vo2_max` | Sample | list, reconcile, rollup, dailyRollup | activity_and_fitness | |
| [Sedentary Period](/health/reference/rest/v4/users.dataTypes.dataPoints#sedentaryperiod) | `sedentary_period` | `sedentary_period` | Interval | list, reconcile, rollup, dailyRollup | activity_and_fitness | |
| [Sleep](/health/reference/rest/v4/users.dataTypes.dataPoints#sleep) | `sleep` | `sleep` | Session | list, get, reconcile, create, update, batchDelete | sleep | |
| [Steps](/health/reference/rest/v4/users.dataTypes.dataPoints#steps) | `steps` | `steps` | Interval | list, reconcile, rollup, dailyRollup | activity_and_fitness | |
| [Swim Lengths Data](/health/reference/rest/v4/users.dataTypes.dataPoints#swimlengthsdata) | `swim-lengths-data` | `swim_lengths_data` | Interval | list, reconcile, rollup, dailyRollup | activity_and_fitness | |
| [Time in Heart Rate Zone](/health/reference/rest/v4/users.dataTypes.dataPoints#timeinheartratezone) | `time-in-heart-rate-zone` | `time_in_heart_rate_zone` | Interval | reconcile, rollup, dailyRollup | activity_and_fitness | |
| [Total Calories](/health/reference/rest/v4/users.dataTypes.dataPoints#totalcalories) | `total-calories` | `total_calories` | Interval | rollup, dailyRollup | activity_and_fitness | |
| [VO2 Max](/health/reference/rest/v4/users.dataTypes.dataPoints#vo2max) | `vo2-max` | `vo2_max` | Sample | list, reconcile | activity_and_fitness | |
| [Weight](/health/reference/rest/v4/users.dataTypes.dataPoints#weight) | `weight` | `weight` | Sample | list, get, reconcile, rollup, dailyRollup, create, update, batchDelete | health_metrics_and_measurements | |

## Data Availability

User data updates occur only after activity tracker synchronization or manual data entry through the Fitbit mobile or web app. The Fitbit device and mobile app automatically sync every 15 minutes when the app is open with active data connection and Bluetooth range. MobileTrack syncs every hour while the app remains open.

## Distance Standards

Exercise distances, such as `elevationGainMillimeters`, use millimeters as the standard unit for the following reasons:

1. **Maintaining Data Precision**: Millimeters ensure no precision loss when reading and providing data, allowing high-accuracy measurements.

2. **Standardization**: Millimeters serve as the designed standardized unit across services, providing consistency for developers using different API parts.

3. **Broad Measurement System Support**: Base-unit millimeters enable developers to convert easily to any chosen unit, supporting metric, imperial, or other systems.

---

## Related Resources

- [Next: User profile information](/health/profile)
