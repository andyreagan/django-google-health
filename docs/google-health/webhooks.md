> Fetched 2026-05-14 from https://developers.google.com/health/webhooks

# Webhook subscriptions

The Google Health API allows your application to receive real-time notifications when a user's health data changes. Instead of polling for changes, your server receives an HTTPS POST request ([webhook](https://en.wikipedia.org/wiki/Webhook)) as soon as data is available in the Google Health API.

## Supported data types

Webhook notifications are supported for the following data types:

* Active Zone Minutes
* Altitude
* Body Fat
* Calories In Heart Rate Zone
* Daily Heart Rate Variability
* Daily Heart Rate Zones
* Daily Oxygen Saturation
* Daily Resting Heart Rate
* Daily Sleep Temperature Derivations
* Distance
* Exercise
* Floors
* Heart Rate
* Sleep
* Steps
* Total Calories
* Weight

Notifications are sent for these data types only when a user has granted consent for one of the corresponding scopes:

* **Activity**, which covers steps, altitude, distance, and floors data types:
  * `https://www.googleapis.com/auth/googlehealth.activity_and_fitness`
  * `https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly`
* **Health Metrics**, which covers the weight data type:
  * `https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements`
  * `https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly`
* **Sleep**, which covers the sleep data type:
  * `https://www.googleapis.com/auth/googlehealth.sleep`
  * `https://www.googleapis.com/auth/googlehealth.sleep.readonly`

## Manage subscribers

Before you can receive notifications, you must register a Subscriber, which represents your application's notification endpoint. You can manage subscribers using the REST API available at [`projects.subscribers`](/health/reference/rest/v4/projects.subscribers).

Your subscriber endpoint must use HTTPS (TLSv1.2+) and be publicly accessible. During subscriber creation and updates, the Google Health API performs a verification challenge to ensure you own the endpoint URI. If verification fails, subscriber creation and update operations fail with a `FailedPreconditionException`.

### Create a subscriber

To register a new subscriber for your project, use the [`create`](/health/reference/rest/v4/projects.subscribers/create) endpoint. You need to provide:

* `project-id`: The project number where the webhook service account was created.
* `subscriberId`: A unique identifier that you provide for the subscriber. This ID must be between 4 and 36 characters, and match the regular expression (`[a-z]([a-z0-9-]{2,34}[a-z0-9])`).
* `endpointUri`: The destination URL for webhook notifications.
* `subscriberConfigs`: The data types you want to receive notifications for, and the subscription policy for each.
* `endpointAuthorization`: The authorization mechanism for your endpoint. This must contain a `secret` that you provide. The value of `secret` is sent in the `Authorization` header with each notification message. You can use this token to verify that incoming requests are from the Google Health API. For example, you can set `secret` to `Bearer R4nd0m5tr1ng123` for Bearer authentication, or `Basic dXNlcjpwYXNzd29yZA==` for Basic authentication.

In `subscriberConfigs` you must set `subscriptionCreatePolicy` for each data type. Set it to `AUTOMATIC` to use automatic subscriptions, or `MANUAL` if you intend to manage user subscriptions yourself. See [automatic subscriptions](#automatic_subscriptions) and [manual subscriptions](#manual_subscriptions) for more details on each option.

#### Request

```
POST https://health.googleapis.com/v4/projects/project-id/subscribers?subscriberId=subscriber-id
{
  "endpointUri": "https://myapp.com/webhooks/health",
  "subscriberConfigs": [
    {
      "dataTypes": ["steps", "altitude", "distance", "floors", "weight"],
      "subscriptionCreatePolicy": "AUTOMATIC"
    },
    {
      "dataTypes": ["sleep"],
      "subscriptionCreatePolicy": "MANUAL"
    }
  ],
  "endpointAuthorization": {
    "secret": "Bearer example-secret-token"
  }
}
```

#### Response

```json
{
  "name": "projects/project-id/subscribers/subscriber-id",
  "endpointUri": "https://myapp.com/webhooks/health",
  "subscriberConfigs": [
    {
      "dataTypes": ["steps", "altitude", "distance", "floors", "weight"],
      "subscriptionCreatePolicy": "AUTOMATIC"
    },
    {
      "dataTypes": ["sleep"],
      "subscriptionCreatePolicy": "MANUAL"
    }
  ]
}
```

### List subscribers

Use the [`list`](/health/reference/rest/v4/projects.subscribers/list) endpoint to retrieve all subscribers registered for your project.

#### Request

```
GET https://health.googleapis.com/v4/projects/project-id/subscribers
```

#### Response

```json
{
  "subscribers": [
    {
      "name": "projects/project-id/subscribers/subscriber-id",
      "endpointUri": "https://myapp.com/webhooks/health",
      "subscriberConfigs": [
        {
          "dataTypes": ["steps", "altitude", "distance", "floors", "weight"],
          "subscriptionCreatePolicy": "AUTOMATIC"
        },
        {
          "dataTypes": ["sleep"],
          "subscriptionCreatePolicy": "MANUAL"
        }
      ],
      "endpointAuthorization": {
        "authorizationTokenSet": true
      }
    }
  ],
  "totalSize": 1
}
```

### Update a subscriber

Use the [`patch`](/health/reference/rest/v4/projects.subscribers/patch) endpoint to update a subscriber in your project. The fields that can be updated are `endpointUri`, `subscriberConfigs`, and `endpointAuthorization`.

You update fields by providing an `updateMask` query parameter and a request body. The `updateMask` must contain a comma-separated list of field names that you want to update, using camel case for field names (for example, `endpointUri`). The request body must contain a partial Subscriber object with the new values for fields you want to update. Only fields specified in `updateMask` are updated. If you provide fields in the request body that are not in `updateMask`, they are ignored.

If you update `endpointUri` or `endpointAuthorization`, endpoint verification is performed. See [Endpoint verification](#endpoint_verification) for details.

When updating `subscriberConfigs`, note that it's a **full replacement**, not a merge. If `subscriberConfigs` is included in `updateMask`, all stored configurations for that subscriber are overwritten with list provided in request body. To add or remove a configuration, you must provide the complete set of configurations. If you are updating other fields and want to keep your current configurations, omit `subscriberConfigs` from `updateMask`.

#### Request

```
PATCH https://health.googleapis.com/v4/projects/project-id/subscribers/subscriber-id?updateMask=endpointUri
{
  "endpointUri": "https://myapp.com/new-webhooks/health"
}
```

#### Response

```json
{
  "name": "projects/project-id/subscribers/subscriber-id",
  "endpointUri": "https://myapp.com/new-webhooks/health",
  "subscriberConfigs": [
    {
      "dataTypes": ["steps", "altitude", "distance", "floors", "weight"],
      "subscriptionCreatePolicy": "AUTOMATIC"
    },
    {
      "dataTypes": ["sleep"],
      "subscriptionCreatePolicy": "MANUAL"
    }
  ]
}
```

### Delete a subscriber

Use the [`delete`](/health/reference/rest/v4/projects.subscribers/delete) endpoint to remove a subscriber from your project. Once deleted, the subscriber will no longer receive notifications.

#### Request

```
DELETE https://health.googleapis.com/v4/projects/project-id/subscribers/subscriber-id
```

#### Response

An empty response body with HTTP status `200 OK` is returned if deletion is successful.

```json
{}
```

## Endpoint verification

To ensure the security and reliability of your notification delivery, the Google Health API performs a mandatory two-step verification handshake whenever you create a subscriber or update its endpoint configuration (`endpointUri` or `endpointAuthorization`). This process is performed synchronously during the API call. The service sends two automated POST requests to your endpoint URI, using the User-Agent `Google-Health-API-Webhooks-Verifier`, with the JSON body `{"type": "verification"}`.

* **Authorized Handshake**: The first request is sent with your configured `Authorization` header. Your server must respond with a `200 OK` or `201 Created` status.
* **Unauthorized Challenge**: The second request is sent without credentials. Your server must respond with a `401 Unauthorized` or `403 Forbidden` status.

This handshake confirms that your endpoint is active and correctly enforcing security. If either step fails, the API request fails with a `FAILED_PRECONDITION` error. Only after this handshake succeeds is your subscriber saved and activated to receive health data notifications.

### Key rotation

If you need to rotate keys for `endpointAuthorization`, follow these steps:

1. Configure your endpoint to accept both old and new `endpointAuthorization` values.
2. Update the subscriber configuration with new `endpointAuthorization` value using a `patch` request with `?updateMask=endpointAuthorization`.
3. Configure your endpoint to accept only new `endpointAuthorization` value after confirming step 2 was successful.

## User subscriptions

The Google Health API helps you manage user subscriptions efficiently, reducing the need for manual registration during user onboarding.

### Automatic subscriptions

We recommend using automatic subscriptions. To enable this feature, set `subscriptionCreatePolicy` to `AUTOMATIC` in your `subscriberConfigs` for the specific data types. The `dataTypes` you specify with an `AUTOMATIC` policy are the same data types for which the Google Health API sends notifications, provided user consent is also granted for those data types.

When a user grants application consent for scopes that correspond to data types with an `AUTOMATIC` policy, the Google Health API automatically tracks and sends out notifications for the data types resulting from the intersection between user consented data types and the automatic subscriber config data types for that user. Notifications are then sent to your endpoint whenever that user generates new data for those types. This works for users who grant consent either before or after you create the subscriber. Notifications are not backfilled for data generated before the subscriber was created.

If a user revokes consent, notifications for the corresponding data types will stop. Automatic subscriptions are managed by Google and cannot be listed or deleted individually; they are removed only when the parent subscriber is deleted.

### Manual subscriptions

If you prefer to manage subscriptions for each user manually, set `subscriptionCreatePolicy` to `MANUAL` in `subscriberConfigs`. With this policy, user subscriptions are not created automatically. This functionality will be used in the future when APIs for managing manual subscriptions are made available. Until these APIs are available, we recommend using `AUTOMATIC` subscriptions.

## Notifications

When a user's data changes for a subscribed data type, the Google Health API sends an HTTPS POST request to the subscriber endpoint URL.

### Notification format

The notification payload is a JSON object containing details about the data change. This includes the user ID, data type, and time intervals, which you can use to query the updated data.

```json
{
  "data": {
    "version": "1",
    "clientProvidedSubscriptionName": "subscription-name",
    "healthUserId": "health-user-id",
    "operation": "UPSERT",
    "dataType": "steps",
    "intervals": [
      {
        "physicalTimeInterval": {
          "startTime": "2026-03-0B01:29:00Z",
          "endTime": "2026-03-08T01:34:00Z"
        },
        "civilDateTimeInterval": {
          "startDateTime": {
            "date": {
              "year": 2026,
              "month": 3,
              "day": 7
            },
            "time": {
              "hours": 17,
              "minutes": 29
            }
          },
          "endDateTime": {
            "date": {
              "year": 2026,
              "month": 3,
              "day": 7
            },
            "time": {
              "hours": 17,
              "minutes": 34
            }
          }
        },
        "civilIso8601TimeInterval": {
          "startTime": "2026-03-07T17:29:00",
          "endTime": "2026-03-07T17:34:00"
        }
      }
    ]
  }
}
```

The `operation` field indicates the type of change that triggered the notification:

* **`UPSERT`**: Sent for any data addition or modification.
* **`DELETE`**: Sent when a user deletes data, or when data is removed due to a system event, such as a user revoking permission or deleting their account.

We recommend making your notification handling logic idempotent, especially for `UPSERT` operations, as retries can cause duplicate notifications to be sent.

The `clientProvidedSubscriptionName` field is a unique identifier. For subscriptions with a `MANUAL` policy, this field contains the persistent, developer-provided subscription name specified when the subscription is created. This provides a stable ID for managing manual subscriptions. For subscriptions created with an `AUTOMATIC` policy, the Google Health API automatically generates and assigns a unique identifier (a random UUID) to this field for each notification. Including `clientProvidedSubscriptionName` for both manual and automatic policies ensures a consistent notification payload format across all subscription types.

The `healthUserId` is a Google Health API identifier for the user whose data has changed. If your application supports multiple users, you could receive notifications for any user who has granted your application consent. When you receive a notification, use `healthUserId` to identify which user's data has changed, so you can use their OAuth credentials to query their data.

To map a user's OAuth credentials to their `healthUserId`, use the [`getIdentity`](/health/reference/rest/v4/users/getIdentity) endpoint. Call this endpoint with a user's credentials during user onboarding to retrieve their `healthUserId`, and store this mapping. This mapping doesn't change over time, so it can be cached indefinitely. For an example, see [Get user ID](/health/endpoints#get-user-id). This lets you select the correct user credentials when querying data based on the `healthUserId` in a notification.

### Respond to a notification

Your server must respond to notifications with an HTTP `204 No Content` status code immediately. To avoid timeouts, process the notification payload asynchronously after sending the response. If the Google Health API receives any other status code or the request times out, it retries sending the notification later.

Node.js (Express) Example:

```javascript
app.post('/webhook-receiver', (req, res) => {
    // 1. Immediately acknowledge the notification
    res.status(204).send();

    // 2. Process the data asynchronously in the background
    const notification = req.body;
    setImmediate(() => {
        console.log(`Update for user ${notification.data.healthUserId} of type ${notification.data.dataType}`);
        // Trigger your data retrieval logic here
    });
});
```

## Subscriber status and recovery

If your subscriber endpoint becomes unavailable or returns an error status code (anything other than `204`), the Google Health API stores pending notifications for up to 7 days and retries delivery with exponential backoff.

Once your endpoint is back online and responds with `204`, the API automatically delivers the backlog of stored messages. Notifications older than 7 days are discarded and cannot be recovered.
