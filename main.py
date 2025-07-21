import os
import json
import base64
import logging
import re
import mimetypes
from typing import Dict, Any, List, Tuple, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import google.auth
import google.auth.transport.requests
from google.cloud import storage
import requests, markdown
from requests import exceptions as requests_exceptions

import aiohttp
app = FastAPI(static_files_directory="public", title="Gemini RAG Chatbot API", version="1.0.0")



# --- Configuration ---
class Config:
    """애플리케이션 설정을 중앙에서 관리하는 클래스."""
    PROJECT_ID = os.environ.get('PROJECT_ID', 'cheom-rag-test1')
    LOCATION_ID = os.environ.get('LOCATION_ID', 'us-central1')
    MODEL_ID = os.environ.get('MODEL_ID', 'gemini-2.5-flash')
    DATASTORE_ID = os.environ.get('DATASTORE_ID', 'testbringer_1752021252943_gcs_store')
    DATASTORE_LOCATION = os.environ.get('DATASTORE_LOCATION', 'global')

    API_ENDPOINT = f"https://{LOCATION_ID}-aiplatform.googleapis.com"
    MODEL_ENDPOINT_URL = f"{API_ENDPOINT}/v1/projects/{PROJECT_ID}/locations/{LOCATION_ID}/publishers/google/models/{MODEL_ID}:generateContent"
    DATASTORE_PATH = f"projects/{PROJECT_ID}/locations/{DATASTORE_LOCATION}/collections/default_collection/dataStores/{DATASTORE_ID}"

    SPANNER_PROJECT = os.environ.get("SPANNER_PROJECT", "cheom-rag-test1")
    SPANNER_INSTANCE = os.environ.get("SPANNER_INSTANCE", "cheomspanner")
    SPANNER_DB = os.environ.get("SPANNER_DB", "testspanner")

    SYSTEM_INSTRUCTION = """너는 SaaS 솔루션 기업 **"처음서비스"**의 고객지원 담당자야.  
처음서비스는 한국 기반의 회사로, 주요 고객은 모두 한국 사용자이며, 서비스는 다음과 같아:

- 메일 대량 발송 대행 서비스
- 뉴스레터 제작 솔루션
- 기프티콘 발송 대행 서비스
- 온라인 설문 조사 대행 서비스

---

💼 **너의 역할**

- 고객이 처음서비스에 대해 질문하면, 사내 매뉴얼 및 검색된 RAG 문서 내용을 바탕으로 **친절하고 자세한 한국어로 응답**해야 해.
- **절대 상상하거나 문서에 없는 내용을 답하지 마.**
- 사용자가 웹사이트 스크린샷을 첨부한 경우, 해당 이미지를 바탕으로 문제를 분석하고 답변에 적극 반영해.

---

🧠 **답변 작성 규칙**

- 응답은 반드시 **검색된 문서 내용(RAG)만 바탕**으로 구성해.
- 문서에 내용이 없거나 불충분할 경우, 그 사실을 명확히 알리고, 안내 가능한 범위 내에서만 설명해.
- 답변은 **친절하지만 간결한 한국어**로 진행해.
- 각 항목은 보기 좋게 다음 형식을 따라야 해:

📌 **항목 출력 형식**

[기능명 또는 항목 제목]: [기능 설명]

- 항목마다 줄바꿈(Line break)할 것.
- 항목 간에 줄 간격 없이 연속 출력.
- 불필요한 마크다운, 공백 줄 삽입 금지.

---

🔗 **참고 문서 링크 규칙**

- 답변 마지막에 RAG로 참고한 문서를 **클릭 가능한 하이퍼링크 형식으로 첨부해**.
- 링크의 경우, 참고한 gcs RAG 링크로만 제공해. 다른 링크는 제공하지 마.
- 링크가 2개 이상일 경우, 리스트 형식으로 나열.
- 형식은 아래와 같아야 해:

👉 관련 문서 보기:

- 문서 제목 1

- 문서 제목 2

📥 **입력 변수 형식 예시**

질문: {{user_question}}
검색 문서(RAG): {{retrieved_chunks}} ← 텍스트 or JSON
스크린샷(선택): {{image_data}} ← base64 or URL

---

이제 위 기준에 따라 고객의 질문에 대해 응답해줘.


"""

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Google Cloud Authentication ---
# Cloud Run 환경에서는 서비스 계정을 통해 자동으로 인증 정보를 가져옵니다.
try:
    credentials, project_id = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    storage_client = storage.Client(credentials=credentials)
except google.auth.exceptions.DefaultCredentialsError:
    logger.critical("Authentication failed. Could not find default Google Cloud credentials.")
    credentials = None
    storage_client = None

# --- Custom Exceptions ---
class VertexAIAPIError(Exception):
    """Custom exception for Vertex AI API errors."""
    def __init__(self, message: str, status_code: int, error_body: str):
        super().__init__(message)
        self.status_code = status_code
        self.error_body = error_body

# --- Helper Functions ---
from utils.spanner import query_spanner_triples  # ← import 추가

async def _build_vertex_payload(
    user_prompt: str,
    conversation_history: List[Dict[str, Any]],
    image_file: Optional[UploadFile]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:

    user_content_parts = []

    # ⬇️ Spanner Triple 검색
    triples = query_spanner_triples(
        user_prompt,
        Config.SPANNER_PROJECT,
        Config.SPANNER_INSTANCE,
        Config.SPANNER_DB
    )
    if triples:
        triple_str = "\n".join([f"- {t}" for t in triples])
        user_content_parts.append({
            "text": f"[스패너 Triple 지식]\n{triple_str}"
        })

    if image_file:
        image_base64 = base64.b64encode(await image_file.read()).decode('utf-8')
        user_content_parts.append({
            "inlineData": {"mimeType": image_file.content_type, "data": image_base64}
        })

    if user_prompt:
        user_content_parts.append({"text": f"[사용자 질문]\n{user_prompt}"})

    if not user_content_parts:
        raise ValueError("User prompt or image is required.")

    current_contents = conversation_history + [{"role": "user", "parts": user_content_parts}]

    payload = {
        "systemInstruction": {"parts": [{"text": Config.SYSTEM_INSTRUCTION}]},
        "contents": current_contents,
        "tools": [  # Vertex AI Search도 여전히 활성화
            {
                "retrieval": {
                    "vertexAiSearch": {"datastore": Config.DATASTORE_PATH}
                }
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
            "topP": 0.3
        }
    }
    return payload, current_contents


async def _call_vertex_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    """주어진 페이로드로 Vertex AI API를 호출하고 응답을 반환합니다."""
    if not credentials:
        raise ConnectionAbortedError("Server authentication is not configured.")

    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    
    headers = {
        'Authorization': f'Bearer {credentials.token}',
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    async with aiohttp.ClientSession() as session:
        logger.info(f"Sending request to Vertex AI model: {Config.MODEL_ID}")
        async with session.post(Config.MODEL_ENDPOINT_URL, headers=headers, json=payload, timeout=300) as response:
            if not response.ok:
                error_body = await response.text()
                raise VertexAIAPIError(
                    message=f"HTTP error {response.status} for URL {response.url}",
                    status_code=response.status,
                    error_body=error_body
                )
            return await response.json()

# --- API Route ---
@app.post('/api/generate')
async def generate_content(
    userPrompt: str = Form(""),
    conversationHistory: str = Form("[]"),
    imageFile: Optional[UploadFile] = File(None)
):
    """사용자 입력을 받아 Vertex AI와 통신하고 결과를 반환합니다."""
    if not credentials:
        raise HTTPException(status_code=503, detail={"error": {"message": "Server authentication failed."}})

    try:
        conversation_history = json.loads(conversationHistory)
        payload, current_contents = await _build_vertex_payload(userPrompt, conversation_history, imageFile)
        api_data = await _call_vertex_api(payload)
        model_response_content = api_data.get('candidates', [{}])[0].get('content')
        updated_history = list(current_contents)

        if model_response_content:
            # GCS 링크(gs://...)를 웹에서 접근 가능한 프록시 URL(/gcs/...)로 변환합니다.
            # 예: [문서](gs://bucket/file.pdf) -> [문서](/gcs/bucket/file.pdf)
            model_text = model_response_content['parts'][0]['text']
            proxied_text = re.sub(r'\(gs:\/\/([^)]+)\)', r'(/gcs/\1)', model_text)

            # 링크가 수정된 마크다운을 HTML로 변환
            html_content = markdown.markdown(proxied_text)
            model_response_content['parts'][0]['text'] = html_content
            updated_history.append(model_response_content)
        return JSONResponse({"vertexAiResponse": api_data, "updatedHistory": updated_history})

    except ValueError as ve:
        logger.warning(f"Bad Request from client: {ve}")
        raise HTTPException(status_code=400, detail={"error": {"message": str(ve)}})
    except json.JSONDecodeError:
        logger.warning("Failed to decode conversation history JSON from request.")
        raise HTTPException(status_code=400, detail={"error": {"message": "Invalid conversation history format."}})
    except VertexAIAPIError as api_err:
        status_code = api_err.status_code
        error_body = api_err.error_body
        user_message = f"AI 서비스에서 예상치 못한 오류가 발생했습니다. (코드: {status_code})"

        if status_code == 400:
            logger.warning(f"Vertex AI Bad Request (400): {error_body}")
            user_message = "요청이 잘못되었습니다. 입력 내용(토큰 수, 형식 등)을 확인해주세요."
        elif status_code == 403:
            logger.error(f"Vertex AI Permission Denied (403): {error_body}. Check service account IAM roles.")
            user_message = "AI 서비스에 접근할 권한이 없습니다. 서버 관리자에게 문의하세요."
        elif status_code == 404:
            logger.error(f"Vertex AI Resource Not Found (404): {error_body}. Check model or datastore ID.")
            user_message = "요청한 AI 리소스(모델, 데이터스토어 등)를 찾을 수 없습니다."
        elif status_code == 429:
            logger.warning(f"Vertex AI Quota Exceeded (429): {error_body}")
            user_message = "API 사용량이 할당량을 초과했습니다. 잠시 후 다시 시도해주세요."
        elif status_code == 500:
            logger.error(f"Vertex AI Internal Server Error (500): {error_body}")
            user_message = "AI 서비스에 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        elif status_code >= 503:
            logger.error(f"Vertex AI Service Unavailable (503): {error_body}")
            user_message = "AI 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요."
        else:
            logger.error(f"Vertex AI API Unhandled HTTP error ({status_code}): {api_err} - Body: {error_body}")

        raise HTTPException(status_code=status_code, detail={"error": {"message": user_message, "details": error_body}})
    except requests_exceptions.Timeout as timeout_err:
        logger.error(f"Request to Vertex AI timed out: {timeout_err}")
        raise HTTPException(status_code=504, detail={"error": {"message": "AI 서비스 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."}})
    except requests_exceptions.RequestException as req_err:
        logger.error(f"Network error calling Vertex AI API: {req_err}")
        raise HTTPException(status_code=504, detail={"error": {"message": "AI 서비스에 연결하는 중 네트워크 오류가 발생했습니다."}})
    except ConnectionAbortedError as auth_err:
        logger.error(f"Authentication error: {auth_err}")
        raise HTTPException(status_code=401,detail={"error": {"message": "서버 인증이 설정되지 않았습니다. 관리자에게 문의하세요."}})
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500,detail={"error": {"message": "예기치 않은 서버 오류가 발생했습니다."}})


# --- GCS Proxy Route ---
@app.get("/gcs/{bucket_name}/{file_path:path}")
async def proxy_gcs_file(bucket_name: str, file_path: str):
    """
    GCS에 저장된 파일을 프록시하여 사용자에게 스트리밍합니다.
    gs:// 링크를 웹에서 직접 접근할 수 있도록 변환하는 역할을 합니다.
    """
    if not storage_client:
        logger.error("Storage client not initialized due to authentication failure.")
        raise HTTPException(status_code=503, detail="서버의 스토리지 서비스 연결에 실패했습니다.")

    try:
        logger.info(f"Proxying GCS file: gs://{bucket_name}/{file_path}")
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)

        if not blob.exists():
            logger.warning(f"File not found in GCS: gs://{bucket_name}/{file_path}")
            raise HTTPException(status_code=404, detail="요청한 파일을 찾을 수 없습니다.")

        # 파일을 스트리밍하기 위한 제너레이터
        def iterfile():
            with blob.open("rb") as f:
                yield from f

        # 파일의 MIME 타입을 추측하여 Content-Type 헤더 설정
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = "application/octet-stream"  # 기본값

        # 브라우저에서 바로 열리도록 Content-Disposition 헤더 설정
        headers = {'Content-Disposition': f'inline; filename="{os.path.basename(file_path)}"'}
        return StreamingResponse(iterfile(), media_type=content_type, headers=headers)

    except Exception as e:
        logger.error(f"Error proxying GCS file gs://{bucket_name}/{file_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="파일을 가져오는 중 서버 오류가 발생했습니다.")


# --- Route for the root path ("/") ---
@app.get("/")
async def serve_root():
    """Serve the SPA's index.html for the root path."""
    return FileResponse("public/index.html")
# --- Static File & SPA Routing ---
app.mount("/", StaticFiles(directory="public"), name="static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve the SPA for any path not matching the API or static files."""
    if full_path.startswith("api") or os.path.exists(os.path.join("public", full_path)):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse("public/index.html")


# --- API Documentation ---
# FastAPI는 /openapi.json에서 OpenAPI 스키마를 자동으로 제공합니다.
# Swagger UI는 /docs에서, ReDoc은 /redoc에서 확인할 수 있습니다.
# (별도의 코드 추가 없이 FastAPI 자체 기능으로 제공)

# 필요하다면, app.openapi() 함수를 오버라이딩하여 스키마를 수정할 수 있습니다.
