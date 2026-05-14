> Fetched 2026-05-14 from https://developers.google.com/health/reference/rest

# Google Health API

The Google Health API lets you view and manage health and fitness metrics and measurement data.

## REST Resource: v4.projects.subscribers

Methods

### create

`POST /v4/{parent=projects/*}/subscribers`

Registers a new subscriber endpoint to receive notifications.

### delete

`DELETE /v4/{name=projects/*/subscribers/*}`

Deletes a subscriber registration.

### list

`GET /v4/{parent=projects/*}/subscribers`

Lists all subscribers registered within the owned Google Cloud Project.

### patch

`PATCH /v4/{subscriber.name=projects/*/subscribers/*}`

Updates the configuration of an existing subscriber, such as the endpoint URI or the data types it's interested in.

## REST Resource: v4.users

Methods

### getIdentity

`GET /v4/{name=users/*/identity}`

Gets the user's identity.

### getProfile

`GET /v4/{name=users/*/profile}`

Returns user Profile details.

### getSettings

`GET /v4/{name=users/*/settings}`

Returns user settings details.

### updateProfile

`PATCH /v4/{profile.name=users/*/profile}`

Updates the user's profile details.

### updateSettings

`PATCH /v4/{settings.name=users/*/settings}`

Updates the user's settings details.

## REST Resource: v4.users.dataTypes.dataPoints

Methods

### batchDelete

`POST /v4/{parent=users/*/dataTypes/*}/dataPoints:batchDelete`

Delete a batch of identifiable data points.

### create

`POST /v4/{parent=users/*/dataTypes/*}/dataPoints`

Creates a single identifiable data point.

### dailyRollUp

`POST /v4/{parent=users/*/dataTypes/*}/dataPoints:dailyRollUp`

Roll up data points over civil time intervals for supported data types.

### exportExerciseTcx

`GET /v4/{name=users/*/dataTypes/*/dataPoints/*}:exportExerciseTcx`

Exports exercise data in TCX format.

### get

`GET /v4/{name=users/*/dataTypes/*/dataPoints/*}`

Get a single identifiable data point.

### list

`GET /v4/{parent=users/*/dataTypes/*}/dataPoints`

Query user health and fitness data points.

### patch

`PATCH /v4/{dataPoint.name=users/*/dataTypes/*/dataPoints/*}`

Updates a single identifiable data point.

### reconcile

`GET /v4/{parent=users/*/dataTypes/*}/dataPoints:reconcile`

Reconcile data points from multiple data sources into a single data stream.

### rollUp

`POST /v4/{parent=users/*/dataTypes/*}/dataPoints:rollUp`

Roll up data points over physical time intervals for supported data types.

## Service Information

**Service:** health.googleapis.com

**Discovery document:** [https://health.googleapis.com/$discovery/rest?version=v4](https://health.googleapis.com/$discovery/rest?version=v4)

**Service endpoint:** `https://health.googleapis.com`

To call this service, use the [Google-provided client libraries](https://cloud.google.com/apis/docs/client-libraries-explained).

## Migration Notice

"Start your migration or new app development today! To ensure a seamless experience for your users, we recommend waiting until the **end of May 2026** to officially launch your integration to align with legacy Fitbit account deprecation."
