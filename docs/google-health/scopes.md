> Fetched 2026-05-14 from https://developers.google.com/health/scopes

# Scopes

All Google Health API endpoints that read and write user data require user consent through one or more scopes. When calling Google's OAuth2 auth endpoint, the app must provide the list of scopes. "[The access token issued will only contain the scopes the consenting user has authorized.](https://developers.google.com/health/scopes)"

All Google Health API scopes begin with:

```
https://www.googleapis.com/auth/googlehealth
```

## Available scopes

| Scope | Permission |
|-------|-----------|
| .activity_and_fitness | Add new activity and fitness data to the Fitbit app, edit and delete the data it adds, and see your activity and fitness data from Fitbit. |
| .activity_and_fitness.readonly | See your Fitbit activity and fitness data. |
| .health_metrics_and_measurements | Add new health metrics and measurement data to the Fitbit app, edit and delete the data it adds, and see your Fitbit health metrics and measurement data. |
| .health_metrics_and_measurements.readonly | See your Fitbit health metrics and measurement data. |
| .location.readonly | See your Fitbit GPS location recorded during an exercise. |
| .nutrition | Add new nutrition data to the Fitbit app, edit and delete the data it adds, and see your Fitbit nutrition data. |
| .nutrition.readonly | See your Fitbit nutrition data. |
| .profile | Add new profile data to the Fitbit app, edit and delete the data it adds, and see your Fitbit profile data. |
| .profile.readonly | See your Fitbit profile data. |
| .settings | Add new settings data to the Fitbit app, edit and delete the data it adds, and see your Fitbit app settings data. |
| .settings.readonly | See your Fitbit settings. |
| .sleep | Add new sleep data to the Fitbit app, edit and delete the data it adds, and see your Fitbit sleep data. |
| .sleep.readonly | See your Fitbit sleep data. |
