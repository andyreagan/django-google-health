> Fetched 2026-05-14 from https://developers.google.com/health/codelabs/make-your-first-api-call

# Make your first Google Health API call

## 1. Introduction

Visual Studio Code (VS Code) and the Rest Client extension by Huachao Mao allow you to test the Google OAuth consent flow and the Google Health API. This codelab demonstrates how to setup the Rest Client extension, initiate the authorization flow, and make your first call to a Google Health API endpoint. Alternatively, API calls can be made with `curl` commands.

### What you'll learn

- How to set up VS Code with Rest client extension
- How to set up a client ID within the Google Cloud console
- How to go through Google OAuth 2.0 authorization flow to get an access token and refresh token
- How to make calls to Google Health API endpoints using Rest client

### What you'll need

- Fitbit mobile app
- [Visual Studio Code](https://code.visualstudio.com/)
- [Rest Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) extension by Huachao Mao

#### To set up the Fitbit mobile app:

1. In either the Apple App Store or the Google Play Store, search for the Fitbit mobile app and download it
2. Select the app icon
3. Click **Sign in with Google**
4. Select your Google Account and press the **Continue** button

#### To install the Visual Studio tools:

1. Download VS Code (typically contains the executable)
2. Start VS Code
3. Install the Rest Client extension by Huachao Mao
   - Click the extension icon on the left-hand side of the IDE
   - Search for **REST Client by Huachao Mao** and press **Install**

**Note:** When you first use the extension, VS Code may indicate that it is "Untrusted" or ask you to trust the workspace or extension. This is a standard VS Code security feature for third-party extensions. You must grant trust for the Rest Client extension to function correctly.

## 2. Setup Google Cloud project

You will use the Google Cloud console to create a client ID and enable use of the Google Health API.

1. Sign in into the [Google Cloud console](https://console.cloud.google.com/)
2. To create a new project:
   1. Click **Select a project** from the project picker
   2. In the upper right corner, select **New Project**
   3. Enter your **Project name**
   4. Enter your **Location** (for example, "No organization")
   5. Click the **Create** button
   6. Select your project

### Enable the Google Health API

1. In the upper left-hand corner, click the menu icon
2. Select **APIs & Services > Library**
3. Search for "Google Health API" and enable it

### Setup your OAuth credentials

If you are not in the Google Cloud console, go to [Google Cloud console](https://console.cloud.google.com/).

1. In the upper left-hand corner, click the menu icon
2. Select **APIs & Services > Credentials**
3. At the top center, select **+ Create Credentials > OAuth client ID**
4. Click the **Configure consent screen** button. If the message "Google Auth Platform not configured yet" appears, click the **Get Started** button
5. In section 1:
   1. Enter the **App name**
   2. Enter the **User support email**
   3. Click the **Next** button
6. In section 2:
   1. Select **External**
   2. Click the **Next** button
7. In section 3:
   1. Enter your email address in the **Contact Information** field
   2. Click the **Next** button
8. In section 4:
   1. Click the checkbox to agree to **Google's API Services User Data Policy**
   2. Click the **Create** button
9. In the metrics section, press the button **Create OAuth client**
10. Choose the application type **Web Application**
11. Enter the client ID **name**
12. Leave **Authorized JavaScript origins** empty
13. Under **Authorized redirect URIs**, press **+ Add URI** button and enter "https://www.google.com" as your redirect URI
14. Click the **Create** button
15. The Google Console will show a message that your client ID is created. Either click the **Download JSON** link to download the client ID and client secret, or write down the values. **You won't be able to recover your client's secret afterwards.**
16. Click **OK**. You will return to the "OAuth 2.0 Client IDs" page
17. Your client ID will be added to your project. Click the client ID URL to see the details

**Note:** If you did not download or save your client secret, you must create a new one as you cannot view it again. Click **OK**, then on the **Credentials** page, select your client ID from under **OAuth 2.0 Client IDs**. Go to the **Client Secrets** section and select **+ ADD SECRET**. A new client secret is generated, which you must download or save. For security reasons, you should delete any client secrets that are no longer in use by pressing the delete icon.

### Add test users

1. On the left pane, select **Audience**. You should see the "Publishing status" set to **Testing** and the "User type" set to **External**
2. Under the section "Test users", click the **+ Add users** button and enter the email address for any user whose data you want to retrieve
3. Click the **Save** button

### Add scopes to the client ID

1. On the left pane, select **Data Access**
2. Click the button **Add or remove scopes**
3. In the API column, search for "Google Health API". For this codelab, use the scope `.../auth/googlehealth.activity_and_fitness.readonly`
4. After selecting the scope, press the **Update** button to return to the Data Access page
5. Click the **Save** button

You have finished setting up your client ID.

## 3. Create the authorization flow

1. Open the VS Code app on your machine
2. On the Welcome screen, select **Open**
3. Select a folder to create this project and press **Open**. Your screen should display your folder or project name in the Explorer
4. From the main menu, choose **File -> New Text file**
5. Save the file by choosing **File -> Save As -> Codelab.http**. This places the file in your project. The file extension must be either .http or .rest

### File Variables for the Codelab

Throughout this project, several values are used multiple times:

| Variable | Description |
|----------|-------------|
| `client_id` | The client ID value from the Google console |
| `secret` | The client's secret value from the Google console |
| `redirect_uri` | An endpoint in your app which processes the authorization code. For the codelab, use https://www.google.com |
| `access_token` | The access token created for the user once the consent flow has finished |
| `refresh_token` | The refresh token created for the user once the consent flow has finished |

Add the following code which defines the variables used with this project at the top of the file `Codelab.http`. Fill in the values for the `client_id` and `secret`:

```
@client_id =
@secret =
@redirect_uri = https://www.google.com
@accessToken={{user.response.body.access_token}}
@refreshToken={{user.response.body.refresh_token}}
```

### Authorization URL

The authorization URL initiates the consent flow and is sent to each user whose data you want to access. To build the authorization URL, you need to know Google's OAuth endpoint and use query parameters to specify the client ID, scopes, and redirect location.

Google's OAuth 2.0 endpoint is at **https://accounts.google.com/o/oauth2/v2/auth**. This endpoint is accessible only over HTTPS. Plain HTTP connections are refused.

The Google authorization server supports many query string parameters. The required parameters for web server applications are: `client_id`, `redirect_uri`, `response_type`, and `scope`.

The values for the query parameters are:

| Parameter | Value |
|-----------|-------|
| `client_id` | The client ID value from the Google console |
| `redirect_uri` | An endpoint in your app which processes the authorization code. For the codelab, use https://www.google.com |
| `response_type` | `code` (supported value for web apps) |
| `scope` | The scopes from the Google console with the syntax https://www.googleapis.com followed by the scope name. For example, https://www.googleapis.com/auth/googlehealth.activity_and_fitness. To request multiple scopes, include all scopes separated by spaces (for example, `scope1 scope2 scope3`). When part of the URL, spaces must be URL-encoded (for example, %20). |

Add the following authorization URL. Replace `client-id` with your actual client ID:

```
### Authorization String
https://accounts.google.com/o/oauth2/v2/auth?client_id=client-id&redirect_uri=https://www.google.com&response_type=code&access_type=offline&scope=https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly
```

When a user grants consent, Google provides an authorization code that you exchange for an access token by calling Google's token endpoint. Add the following definition for calling the token endpoint to `Codelab.http` below the authorization string. Replace `authorization-code` with an authorization code in the next step:

```
### AUTHORIZATION ENDPOINTS
######################################################################
# @name user
POST https://oauth2.googleapis.com/token
Content-Type: application/x-www-form-urlencoded

code=authorization-code&client_id={{clientId}}&client_secret={{secret}}&redirect_uri={{redirect_uri}}&grant_type=authorization_code
```

`@name user` references the current user whose data you're accessing.

## 4. Authorize an account and obtain tokens

The authorization string in `Codelab.http` initiates Google's browser-based consent flow. The Rest Client extension may display a **Send Request** link for this URL. Do not use **Send Request** for this specific URL. Instead, copy and paste it into your browser, or use **Ctrl+Click** (Windows/Linux) or **Cmd+Click** (Mac) in VS Code to open it in your default browser.

```
https://accounts.google.com/o/oauth2/v2/auth?client_id=client-id&redirect_uri=https://www.google.com&response_type=code&access_type=offline&scope=https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly
```

1. You will be asked to sign into your Google Account. Sign in using one of the test user accounts you configured in the **Add test users** section
2. You may be presented with a message stating the app is not verified. This is because the app has not been published. Press "Continue"
3. The consent page lists the scopes being requested. The user can select which scopes they want to share with this app. Click "Continue"

After consenting, you are redirected to the `redirect_uri` you specified (https://www.google.com). Google appends an authorization code to the URL, so the URL in your browser's address bar should look something like:

```
https://www.google.com/?code=4/0Ab32j93oyGWqaXE112sP1IKmh3kV1fE4tcHIMXYJQYWgNEtAa_0-YsfkS9Ekj3Be89u3fw&scope=https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly
```

The authorization code is the alphanumeric value between "code=" and "&scope". In the above example:

```
4/0Ab32j93oyGWqaXE112sP1IKmh3kV1fE4tcHIMXYJQYWgNEtAa_0-YsfkS9Ekj3Be89u3fw
```

In a production app, your server would parse this from the URL parameters. For this codelab, copy the authorization code from the URL in your browser.

Now, exchange this authorization code for an `access_token` and `refresh_token`. In `Codelab.http`, replace `authorization-code` in the POST `/token` request body with the authorization code you copied:

```
POST https://oauth2.googleapis.com/token
Content-Type: application/x-www-form-urlencoded

code=authorization-code&client_id={{client_id}}&client_secret={{secret}}&redirect_uri={{redirect_uri}}&grant_type=authorization_code
```

Click the **Send Request** link above the line `POST https://oauth2.googleapis.com/token`.

The response should look similar to:

```json
{
  "access_token": "ya29.a0ATi6K2uasci7FyyIClNLtQou6z...",
  "expires_in": 3599,
  "refresh_token": "1//05EuqYpEXjJCHCgYIA...",
  "scope": "https://www.googleapis.com/auth/googlehealth.activity_and_fitness",
  "token_type": "Bearer",
  "refresh_token_expires_in": 604799
}
```

When you receive this response, Rest Client automatically populates the `@accessToken` and `@refreshToken` variables defined at the top of `Codelab.http` for use in subsequent requests.

**Note:** The tokens are only stored in this session. If you close the VS Code window, you will need to complete the authorization flow again.

### About refresh tokens

When you exchange the authorization code, the response may include a `refresh_token` in addition to the `access_token`. Access tokens are short-lived (typically 1 hour). When an `access_token` expires, use the `refresh_token` to obtain a new `access_token` without requiring the user to sign in or consent again. This is possible because we included `access_type=offline` in our authorization request.

If you don't receive a `refresh_token` in the response, it may be because you have already granted consent for this app and scopes. Refresh tokens are typically only issued the first time a user grants consent for your app, or when `prompt=consent` is added to the authorization URL to force the consent screen to appear.

The `refresh_token` is long-lived but can expire or become invalid if not used for 6 months, if the user revokes access to your app, or for other reasons. Securely store `refresh_token` for future use.

For more details, see [Refreshing an access token (offline access)](https://developers.google.com/identity/protocols/oauth2/web-server#offline).

## 5. Add data to the Fitbit mobile app

For new users to Fitbit, you might not have data in your Fitbit account to query. Manually add an exercise log to query through one of the endpoints. To manually record an exercise:

1. Open the Fitbit mobile app on your device and sign into your Fitbit account if needed
2. In the bottom right-hand corner of the screen, tap the + button
3. In the section "Manually log", tap **Activity**
4. Search for the exercise type **Walk** and select it
5. Enter a **start time** for today
6. Change the duration to **15 minutes**
7. Leave the distance as **1.0 mi**
8. Tap **Add**
9. Sync the mobile app to the Fitbit servers by long pressing on the screen and sliding it down. When you release your finger, the mobile app will sync
10. In the "Activity" section, you should see your manually logged Walk entry

## 6. Retrieve data using the list method

To call the `list` method, add the following code to `Codelab.http` just below the `/token` endpoint:

```
### users.dataTypes.dataPoints
#####################################################

### LIST exercise
GET https://health.googleapis.com/v4/users/me/dataTypes/exercise/dataPoints
Authorization: Bearer {{accessToken}}
Accept: application/json
```

This code calls the `list` endpoint to display the exercise data recorded by the user in their Fitbit account. To execute the call, press the **Send Request** link for the GET endpoint. Your response should look similar to:

```json
{
  "dataPoints": [
    {
      "name": "users/2515055256096816351/dataTypes/exercise/dataPoints/8896720705097069096",
      "dataSource": {
        "recordingMethod": "MANUAL",
        "platform": "FITBIT"
      },
      "exercise": {
        "interval": {
          "startTime": "2026-02-23T13:10:00Z",
          "startUtcOffset": "-18000s",
          "endTime": "2026-02-23T13:25:00Z",
          "endUtcOffset": "-18000s"
        },
        "exerciseType": "WALKING",
        "metricsSummary": {
          "caloriesKcal": 16,
          "distanceMillimiters": 1609344,
          "steps": "2038",
          "averagePaceSecondsPerMeter": 0.55923407301360051,
          "activeZoneMinutes": "0"
        },
        "exerciseMetadata": {},
        "displayName": "Walk",
        "activeDuration": "900s",
        "exerciseEvents": [
          {
            "eventTime": "2026-02-23T13:10:00Z",
            "eventUtcOffset": "-18000s",
            "exerciseEventType": "START"
          },
          {
            "eventTime": "2026-02-23T13:25:00Z",
            "eventUtcOffset": "-18000s",
            "exerciseEventType": "STOP"
          }
        ],
        "updateTime": "2026-02-24T01:19:22.450466Z"
      }
    }
  ],
  "nextPageToken": ""
}
```

Many endpoints support query parameters for filtering or pagination. For example, exercise supports the filter `interval.civil_start_time`. Add the following request to `Codelab.http` to list exercises within a specific time range:

```
### LIST exercise >= civil start time
GET https://health.googleapis.com/v4/users/me/dataTypes/exercise/dataPoints?filter=exercise.interval.civil_start_time >= "2026-02-22T00:00:00"
Authorization: Bearer {{accessToken}}
Accept: application/json
```

## 7. Congratulations

You have completed the basic codelab and successfully learned how to use Visual Studio Code and the Rest Client extension to test OAuth 2.0 authorization and make calls to Google Health API endpoints. From here, you can add the additional endpoints as demonstrated in the [Retrieve Data using the List method](#6-retrieve-data-using-the-list-method) section.

For more information, explore other Google Health API endpoints in the [reference documentation](/health/reference/rest) and learn more about [Google OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server).
