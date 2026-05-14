> Fetched 2026-05-14 from https://developers.google.com/health/migration

# Migration Guide | Google Health API

## Overview

The Google Health API represents a strategic redesign for querying Fitbit user data, incorporating "enhanced security, consistency, and future-proofing" through modern protocols and standardized data handling. This guide assists developers transitioning from the Fitbit Web API.

## Why Migrate?

Key advantages include:

- **Enhanced Security**: Alignment with Google's security, privacy, and identity standards
- **Consistency**: Standardized data formats, time zones, measurement units, and error handling
- **Scalability & Future-Proofing**: Modern protocol support including gRPC

## App Registration

All Google Health API apps require registration via [Google Cloud Console](https://console.cloud.google.com/).

### Registration Differences

| Aspect | Fitbit Web API | Google Health API |
|--------|---|---|
| **Public Link** | https://dev.fitbit.com/apps | https://console.cloud.google.com |
| **Setup Process** | Register new app directly | Create Google Cloud Project; Enable Google Health API |
| **Basic Fields** | Application Name, Description, URLs, Organization details | Application name, support email, audience, contact email, logo, URLs, authorized domain |
| **Application Types** | Server, Client, Personal | Web application, Android, Chrome Extension, iOS, TVs, Desktop app, Windows platform |
| **Client ID** | Registered with settings save | Registered separately |
| **Access Control** | App-level read/write | Scope-level read/write |
| **URLs** | Redirect URL | Authorized JavaScript Origins, Redirect URL |

## OAuth Implementation

Google Health API exclusively supports [Google OAuth2 Client libraries](https://developers.google.com/identity/protocols/oauth2#libraries).

### OAuth Comparison

| Feature | Fitbit Web API | Google Health API |
|---------|---|---|
| **Library Support** | Open Source | Google OAuth2 Client libraries |
| **Functionality** | Inconsistent across platforms | Consistent across platforms |
| **Authorization URL** | https://www.fitbit.com/oauth2/authorize | https://accounts.google.com/o/oauth2/v2/auth |
| **Token URL** | https://api.fitbit.com/oauth2/token | https://oauth2.googleapis.com/token |
| **Access Token Lifetime** | 8 hours | 1 hour |
| **Access Token Size** | 1024 bytes | 2048 bytes |
| **Refresh Token** | Single token; never expires; one-time use | Multiple tokens per user; 6-month inactivity expiration; time-based options available |
| **Token Response** | Includes user ID in response | User ID obtained via **users.getIdentity** endpoint |

## User Re-authentication

Users must re-consent to your new integration. Access tokens and refresh tokens from the Fitbit Web API cannot be transferred to the Google Health API.

## Scopes

Google Health API scopes follow the format: `https://www.googleapis.com/auth/googlehealth.{scope}`

### Scope Mappings

| Fitbit Web API Scope | Google Health API Scopes |
|---|---|
| activity | .activity_and_fitness, .activity_and_fitness.readonly |
| cardio_fitness | .activity_and_fitness, .activity_and_fitness.readonly |
| heartrate | .health_metrics_and_measurements, .health_metrics_and_measurements.readonly |
| location | .location.readonly |
| nutrition | .nutrition, .nutrition.readonly |
| oxygen_saturation | .health_metrics_and_measurements, .health_metrics_and_measurements.readonly |
| profile | .profile, .profile.readonly |
| respiratory_rate | .health_metrics_and_measurements, .health_metrics_and_measurements.readonly |
| settings | .settings, .settings.readonly |
| sleep | .sleep, .sleep.readonly |
| temperature | .health_metrics_and_measurements, .health_metrics_and_measurements.readonly |
| weight | .health_metrics_and_measurements, .health_metrics_and_measurements.readonly |

## Data Types

### Data Type Mappings

| Fitbit Web API Data Type | Google Health API Data Type |
|---|---|
| Active Zone Minutes | [Active Zone Minutes](/health/reference/rest/v4/users.dataTypes.dataPoints#activezoneminutes) (`active-zone-minutes`) |
| Contains changes to the user's activity levels | [Activity Level](/health/reference/rest/v4/users.dataTypes.dataPoints#activitylevel) (`activity-level`) |
| Elevation | [Altitude](/health/reference/rest/v4/users.dataTypes.dataPoints#altitude) (`altitude`) |
| Body fat | [Body Fat](/health/reference/rest/v4/users.dataTypes.dataPoints#bodyfat) (`body-fat`) |
| caloriesOut in each heart rate zone | [Calories In Heart Rate Zone](/health/reference/rest/v4/users.dataTypes.dataPoints#caloriesinheartratezone) (`calories-in-heart-rate-zone`) |
| HRV summary | [Daily Heart Rate Variability](/health/reference/rest/v4/users.dataTypes.dataPoints#dailyheartratevariability) (`daily-heart-rate-variability`) |
| SpO2 summary | [Daily Oxygen Saturation](/health/reference/rest/v4/users.dataTypes.dataPoints#dailyoxygensaturation) (`daily-oxygen-saturation`) |
| Resting heart rate | [Daily Resting Heart Rate](/health/reference/rest/v4/users.dataTypes.dataPoints#dailyrestingheartrate) (`daily-resting-heart-rate`) |
| Skin temperature | [Daily Sleep Temperature Derivations](/health/reference/rest/v4/users.dataTypes.dataPoints#dailysleeptemperaturederivations) (`daily-sleep-temperature-derivations`) |
| Distance | [Distance](/health/reference/rest/v4/users.dataTypes.dataPoints#distance) (`distance`) |
| Recorded activity | [Exercise](/health/reference/rest/v4/users.dataTypes.dataPoints#exercise) (`exercise`) |
| Floors | [Floors](/health/reference/rest/v4/users.dataTypes.dataPoints#floors) (`floors`) |
| Heart Rate | [Heart Rate](/health/reference/rest/v4/users.dataTypes.dataPoints#heartrate) (`heart-rate`) |
| HRV Intraday | [Heart Rate Variability](/health/reference/rest/v4/users.dataTypes.dataPoints#heartratevariability) (`heart-rate-variability`) |
| SpO2 Intraday | [Oxygen Saturation](/health/reference/rest/v4/users.dataTypes.dataPoints#oxygensaturation) (`oxygen-saturation`) |
| VO2 Max value when the user runs | [Run VO2 Max](/health/reference/rest/v4/users.dataTypes.dataPoints#runvo2max) (`run-vo2-max`) |
| Activity time series minutes sedentary | [Sedentary Period](/health/reference/rest/v4/users.dataTypes.dataPoints#sedentaryperiod) (`sedentary-period`) |
| Sleep | [Sleep](/health/reference/rest/v4/users.dataTypes.dataPoints#sleep) (`sleep`) |
| Steps | [Steps](/health/reference/rest/v4/users.dataTypes.dataPoints#steps) (`steps`) |
| Activity time series swimming strokes | [Swim Lengths Data](/health/reference/rest/v4/users.dataTypes.dataPoints#swimlengthsdata) (`swim-lengths-data`) |
| Activity caloriesOut | [Total Calories](/health/reference/rest/v4/users.dataTypes.dataPoints#totalcalories) (`total-calories`) |
| VO2 Max value | [VO2 Max](/health/reference/rest/v4/users.dataTypes.dataPoints#vo2max) (`vo2-max`) |
| Weight | [Weight](/health/reference/rest/v4/users.dataTypes.dataPoints#weight) (`weight`) |

## Endpoints

- **Service Endpoint**: Base URL changes to https://health.googleapis.com
- **Endpoint Syntax**: Consistent syntax across all data types
- **User Identifier**: Specify user ID or `me` (inferred from access token)

### Example

```
GET https://health.googleapis.com/v4/users/me/profile
```

### Endpoint Mappings

| Fitbit Web API Endpoint Type | Google Health API |
|---|---|
| GET (Log \| Summary \| Daily Summary) single day | **dailyRollup** method with `windowSize` = 1 day |
| GET (Intraday) granular data | **list** method |
| GET (Time Series) by Date or Interval | **rollUp** or **dailyRollUp** method with date range |
| GET (Log List) | **list** method |
| CREATE & UPDATE Logs | **patch** method |
| DELETE Logs | **batchDelete** method |
| GET Profile | **users.getProfile** (user info), **users.getSettings** (units/timezones) |
| UPDATE Profile | **users.updateProfile**, **users.updateSettings** |
| Get User ID | **users.getIdentity** (returns Fitbit legacy and Google user ID) |

## Migrate Your Users

### The Dual-Library Strategy

Since both OAuth2 libraries coexist during migration, manage a bridging period:

#### Parallel Authorization Management

- **Encapsulate Clients**: Create an abstraction layer for "Health Service" requests, abstracting which library is active
- **Database Schema Update**: Add `oauth_type` flag (values: `fitbit` or `google`)
  - New Users: Default to `google`
  - Existing Users: Keep as `fitbit` until re-consent completion

#### The "Step-Up" Re-consent Flow

1. Detect Fitbit Open Source Token when user opens app; trigger "Service Update" notification
2. Launch Google OAuth Flow when user clicks "Update"
3. Replace & Revoke: Save Google OAuth token, update `oauth_type` to `google`, programmatically revoke old Fitbit token

### Maximize User Retention

#### The "Value-First" Communication

Lead with benefits, not technical changes:

- **Enhanced Security**: Google's account protection and 2FA
- **Reliability**: Faster sync times, stable data connections
- **Feature Gating**: New features require the update

#### Smart Timing

- **Don't Interrupt High-Value Tasks**: Avoid re-consent during workouts or food logging
- **The "Nudge" Phase**: First 30 days use dismissible banner
- **The "Hard Cutoff" Phase**: Make re-consent mandatory after several weeks, aligned with deprecation deadlines

### Migration Flow Comparison

| Feature | Fitbit Web API (Legacy) | Google Health API (Google-Identity) |
|---------|---|---|
| Auth Library | Standard Open Source | Google Identity Services / Google Auth |
| User Accounts | Fitbit Legacy Credentials | Google Account |
| Token Type | Fitbit-specific Access/Refresh | Google-issued Access/Refresh |
| Scope Management | Broad permissions | Granular/Incremental permissions |

### Handle Account Migration Nuance

- **Check Token Validity**: Use background worker to detect "Unauthorized" errors indicating account migration
- **Graceful Failures**: Redirect failed Fitbit OAuth calls to custom "Reconnect Fitbit" page using new Google OAuth flow

## Code Examples

### 1. The "Middleware Switch"

```javascript
const { OAuth2Client } = require('google-auth-library');
const FitbitV1Strategy = require('fitbit-oauth2-library').Strategy;

// 1. Initialize the Google Health API Client
const GHAClient = new OAuth2Client(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  process.env.REDIRECT_URI
);

// 2. Create a Unified Fetcher
async function fetchSteps(user) {
  if (user.apiVersion === 4) {
    // ---- GOOGLE OAUTH LIBRARY LOGIC ----
    GHAClient.setCredentials({ refresh_token: user.refreshToken });
    const url = 'GET https://health.googleapis.com/v4/users/me/dataTypes/steps/dataPoints';
    const res = await GHAClient.request({ url });
    return res.data;
  } else {
    // ---- FITBIT WEB API LEGACY LOGIC ----
    // Use your existing Fitbit open-source library logic here
    return callLegacyV1Api(user.accessToken);
  }
}
```

### 2. Migrate the UX Flow

```javascript
app.get('/dashboard', async (req, res) => {
  const user = await db.users.find(req.user.id);

  if (user.apiVersion === 1) {
    // Render a "soft" migration page explaining the Google transition
    return res.render('migrate-to-google', {
      title: "Keep your data syncing",
      message: "Fitbit is moving to Google accounts. Re-connect now to stay updated."
    });
  }

  const data = await fetchSteps(user);
  res.render('dashboard', { data });
});
```

### 3. Key Technical Transitions

| Feature | Fitbit Web API (Legacy) | Google Health API (Google-Identity) |
|---------|---|---|
| Token Endpoint | https://api.fitbit.com/oauth2/token | https://oauth2.googleapis.com/token |
| Auth Library | Standard Open Source | Google Auth |
| Scope Example | activity | https://www.googleapis.com/auth/googlehealth.activity_and_fitness |
| User ID | Fitbit Encoded ID in /oauth2/token response | User ID from users.getIdentity endpoint |

### 4. Retention Checklist

- **Session Persistence**: Do not clear old Fitbit Web API session until Google Health API access_token is verified and saved
- **Auto-Revoke**: Use POST to https://api.fitbit.com/oauth2/revoke after migration completion to prevent duplicate permissions
- **Error Handling**: Redirect 401 Unauthorized Fitbit calls automatically to Google OAuth flow instead of displaying error

---

## Related Resources

- [Google Health API Developer and Terms & Conditions](/health/policies/health-api-developer-terms-and-conditions)
- [Google Health API Developer and User Data Policy](/health/policies/health-api-developer-user-data-policy)
- [Google Health API Research Pledge](/health/policies/health-api-research-pledge)
- [Google Health API User Data and Health Research Policy](/health/policies/health-api-user-data-and-research-policy)
- [Getting Started](/health/get-started)
- [Google Health API Parity Tool](/health/migration/parity-tool)
