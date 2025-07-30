# Google Cloud Vertex AI Search 설정 가이드

이 문서는 GraphRAG 애플리케이션의 핵심 백엔드인 Google Cloud Vertex AI Search (구 Discovery Engine) 설정을 안내합니다. 데이터 소스용 Cloud Storage 버킷 생성부터 데이터 스토어 및 검색 앱 생성, 그리고 애플리케이션에 필요한 API 엔드포인트와 ID를 확인하는 전 과정을 다룹니다.

## 전제 조건

- Google Cloud Platform (GCP) 프로젝트가 생성되어 있어야 합니다.
- `gcloud` CLI가 설치 및 인증되어 있어야 합니다.
- `Vertex AI Search and Conversation` API가 활성화되어 있어야 합니다. (`gcp_setting.md` 참고)

---

## 1단계: 데이터 저장을 위한 Google Cloud Storage(GCS) 버킷 생성

검색 및 답변의 기반이 될 원본 데이터(PDF, HTML, TXT 등)를 저장할 GCS 버킷을 생성합니다.

### 1.1. Cloud Console 사용

1.  Google Cloud Console에서 **Cloud Storage > 버킷**으로 이동합니다.
2.  **'+ 만들기'**를 클릭합니다.
3.  버킷 이름을 지정합니다. (예: `graphrag-data-source`)
4.  리전(Region)을 선택합니다. (예: `asia-northeast3`)
5.  나머지 설정은 기본값으로 두고 **'만들기'**를 클릭합니다.

### 1.2. gcloud CLI 사용

```bash
# [BUCKET_NAME]을 원하는 버킷 이름으로, [LOCATION]을 원하는 리전으로 변경하세요.
gcloud storage buckets create gs://[BUCKET_NAME] --project=[YOUR_PROJECT_ID] --location=[LOCATION]

# 예시
gcloud storage buckets create gs://graphrag-data-source --project=cheom-kdb-test1 --location=asia-northeast3
```

- 생성한 버킷에 검색할 대상이 되는 문서 파일들을 업로드합니다.

---

## 2단계: Vertex AI Search 데이터 스토어 생성

업로드된 데이터가 저장된 GCS 버킷을 Vertex AI Search가 인덱싱할 수 있도록 데이터 스토어를 생성합니다.

1.  Google Cloud Console에서 **Vertex AI Search and Conversation**으로 이동합니다.
2.  왼쪽 메뉴에서 **'데이터 스토어'**를 선택합니다.
3.  **'+ 새 데이터 스토어'**를 클릭합니다.
4.  **'Cloud Storage'**를 선택하고 1단계에서 생성한 GCS 버킷 경로를 입력합니다. (예: `gs://graphrag-data-source`)
5.  데이터 스토어 이름을 지정합니다. (예: `graphrag-datastore`)
6.  **'만들기'**를 클릭하여 데이터 스토어 생성을 완료합니다. 데이터 양에 따라 인덱싱에 시간이 소요될 수 있습니다.

- **[중요]** 생성된 데이터 스토어의 **ID (`DATASTORE_ID`)**를 기록해 둡니다. 이 값은 애플리케이션의 `.env` 파일에 설정해야 합니다.

---

## 3단계: Vertex AI Search 앱 생성 및 데이터 스토어 연결

사용자 쿼리를 처리할 검색/답변 앱을 생성하고, 2단계에서 만든 데이터 스토어를 연결합니다.

1.  Vertex AI Search and Conversation 콘솔의 왼쪽 메뉴에서 **'앱'**을 선택합니다.
2.  **'+ 새 앱'**을 클릭합니다.
3.  앱 유형으로 **'검색'**을 선택합니다.
4.  앱 이름을 지정합니다. (예: `graphrag-search-app`)
5.  **'계속'**을 클릭합니다.
6.  **'데이터 스토어 선택'** 섹션에서 2단계에서 생성한 데이터 스토어(예: `graphrag-datastore`)를 선택합니다.
7.  **'만들기'**를 클릭하여 앱 생성을 완료합니다.

- **[중요]** 생성된 앱을 클릭하여 세부 정보 페이지로 이동한 후, **엔진 ID (`DISCOVERY_ENGINE_ID`)**를 기록해 둡니다. 이 값은 `.env` 파일에 설정해야 합니다.

---

## 4단계: API 엔드포인트 및 환경 변수 확인

애플리케이션 코드(`modules/services/discovery_engine_api.py`)는 여러 ID 값을 조합하여 API 요청 URL을 동적으로 생성합니다. 다음 값들을 확인하여 `.env` 파일에 올바르게 설정해야 합니다.

| 환경 변수 | 설명 | 확인 위치 |
| :--- | :--- | :--- |
| `PROJECT_ID` | Google Cloud 프로젝트 ID | GCP Console 상단 |
| `DISCOVERY_LOCATION` | 데이터 스토어 및 앱의 위치 | 데이터 스토어/앱 생성 시 지정 (보통 `global`) |
| `DISCOVERY_COLLECTION` | 데이터 컬렉션 ID | 보통 `default_collection` |
| `DISCOVERY_ENGINE_ID` | 3단계에서 생성한 검색 앱의 엔진 ID | Vertex AI Search > 앱 > 해당 앱 선택 |
| `DISCOVERY_SERVING_CONFIG` | 검색 설정 ID | 보통 `default_config` 또는 `default_search` |
| `DATASTORE_ID` | 2단계에서 생성한 데이터 스토어 ID | Vertex AI Search > 데이터 스토어 > 해당 데이터 스토어 선택 |

### API 엔드포인트 구조

코드는 다음 구조를 사용하여 API 엔드포인트를 구성합니다.

-   **Search API Endpoint**:
    `https://discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_ID}/locations/{DISCOVERY_LOCATION}/collections/{DISCOVERY_COLLECTION}/engines/{DISCOVERY_ENGINE_ID}/servingConfigs/{DISCOVERY_SERVING_CONFIG}:search`

-   **Answer API Endpoint**:
    `https://discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_ID}/locations/{DISCOVERY_LOCATION}/collections/{DISCOVERY_COLLECTION}/engines/{DISCOVERY_ENGINE_ID}/servingConfigs/{DISCOVERY_SERVING_CONFIG}:answer`

이 값들을 `로컬_환경_설정_가이드.md`에 명시된 `.env` 파일에 정확히 입력하면, 애플리케이션이 성공적으로 Vertex AI Search 서비스와 통신할 수 있습니다.
