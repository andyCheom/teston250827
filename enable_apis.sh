#!/bin/bash

# Set the Google Cloud project
PROJECT_ID="documentation-467305"
echo "Setting GCP project to $PROJECT_ID"
gcloud config set project $PROJECT_ID

# enabled_apis.txt 파일에서 API 목록을 읽어 활성화합니다.

FILE="enabled_apis.txt"

if [ ! -f "$FILE" ]; then
    echo "Error: $FILE not found."
    exit 1
fi

for API in $(cat $FILE); do
    echo "Enabling API: $API for project $PROJECT_ID"
    gcloud services enable $API --project=$PROJECT_ID
done

echo "All APIs enabled successfully."