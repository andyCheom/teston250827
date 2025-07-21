#!/bin/bash

TARGET_PROJECT="cheom-kdb-test1"
API_LIST_PATH="/home/andy/test_web/api_list/api_list.txt"

if [ ! -f "$API_LIST_PATH" ]; then
  echo "❌ API 리스트 파일이 없습니다: $API_LIST_PATH"
  exit 1
fi

while read api; do
  echo "🔧 Enabling $api..."
  gcloud services enable "$api" --project="$TARGET_PROJECT"
done < "$API_LIST_PATH"

echo "✅ 모든 API 활성화 완료!"
