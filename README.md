# stock_screener
A Google Cloud Function that runs daily to search for stocks fitting the Minervini template adjusted to my liking

## Configure GCP
- Create a Google Cloud Project that can do billing
- Enable the following APIs in the project
    - Google Sheets
    - Google Drive
    - Secrets Manager
    - Cloud Functions
- Add the following secrets in the secrets manager
    - default app engine service account json key as a file
        - call it `service_account_json`
        - this can be downloaded from IAM
        - other service account can be created an used
        - if so make sure to grant this account permission to the funcion
- In the IAM console add a new role to give the service account access to secret manager secret accessor
- Create an empty google worksheet titled `Stock Screener`
    - name the first sheet `Screener`
    - share this entire workbook with the service account you are using
    - use their service account email address
- Enable the Cloud Scheduler in GCP
    - Add a new job with a frequency you like, I did every day at 3PM PT
    - Make sure to set the right timezone
    - For the execution use the URL from the cloud function
    

## Create a config.py file
In the root directory create a config.py file that has the following:

```project_id = xxx```

`xxx` is the project ID of your Google Cloud Project

## Deploy

*Make sure to update the project_id*

*Ensure that you have setup gcloud from the command line and it points to your correct GCP project*

`gcloud functions deploy exercise --set-env-vars --project_id=xxxxxxx --runtime python39 --trigger-http --allow-unauthenticated`
