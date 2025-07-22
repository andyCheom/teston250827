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
from google.cloud import storage, spanner
import requests, markdown
from requests import exceptions as requests_exceptions
from dotenv import load_dotenv
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2 import service_account
import aiohttp

app = FastAPI(static_files_directory="public", title="Gemini RAG Chatbot API", version="1.0.0")
load_dotenv()

class Config:
    def get_env(name: str) -> str:
        if name not in os.environ:
            raise EnvironmentError(f"❌ 환경변수 '{name}'가 설정되어 있지 않습니다.")
        return os.environ[name]

    PROJECT_ID = get_env('PROJECT_ID')
    LOCATION_ID = get_env('LOCATION_ID')
    MODEL_ID = get_env('MODEL_ID')
    DATASTORE_ID = get_env('DATASTORE_ID')
    DATASTORE_LOCATION = get_env('DATASTORE_LOCATION')
    SYSTEM_PROMPT_PATH = get_env('SYSTEM_PROMPT_PATH')
    SPANNER_INSTANCE_ID = get_env('SPANNER_INSTANCE_ID')
    SPANNER_DATABASE_ID = get_env('SPANNER_DATABASE_ID')
    SPANNER_TABLE_NAME = get_env('SPANNER_TABLE_NAME')

    API_ENDPOINT = f"https://{LOCATION_ID}-aiplatform.googleapis.com"
    MODEL_ENDPOINT_URL = f"{API_ENDPOINT}/v1/projects/{PROJECT_ID}/locations/{LOCATION_ID}/publishers/google/models/{MODEL_ID}:generateContent"
    DATASTORE_PATH = f"projects/{PROJECT_ID}/locations/{DATASTORE_LOCATION}/collections/default_collection/dataStores/{DATASTORE_ID}"

    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        SYSTEM_INSTRUCTION = f.read()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SERVICE_ACCOUNT_PATH = "keys/cheom-kdb-test1-faf5cf87a1fd.json"
try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_PATH,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    project_id = credentials.project_id
    storage_client = storage.Client(credentials=credentials, project=project_id)
    spanner_client = spanner.Client(credentials=credentials, project=project_id)
    logger.info(f"✅ 인증 성공 - project_id: {project_id}")
except Exception as e:
    logger.critical("❌ 인증 오류", exc_info=True)
    credentials = None
    storage_client = None
    spanner_client = None

class VertexAIAPIError(Exception):
    def __init__(self, message: str, status_code: int, error_body: str):
        super().__init__(message)
        self.status_code = status_code
        self.error_body = error_body

def query_spanner_triples(user_prompt: str) -> List[str]:
    try:
        logger.info(json.dumps({
            "stage": "spanner_query_start",
            "input": user_prompt
        }))

        instance = spanner_client.instance(Config.SPANNER_INSTANCE_ID)
        database = instance.database(Config.SPANNER_DATABASE_ID)
        query = f"""
        SELECT subject, predicate, object FROM `{Config.SPANNER_TABLE_NAME}`
        WHERE subject LIKE @term OR predicate LIKE @term OR object LIKE @term
        LIMIT 10
        """
        params = {"term": f"%{user_prompt}%"}
        param_types = {"term": spanner.param_types.STRING}

        with database.snapshot() as snapshot:
            results = snapshot.execute_sql(query, params=params, param_types=param_types)
            triples = [f"{row[0]} {row[1]} {row[2]}" for row in results]

        logger.info(json.dumps({
            "stage": "spanner_query_success",
            "input": user_prompt,
            "result_count": len(triples),
            "results": triples
        }))

        return triples

    except Exception as e:
        logger.error(json.dumps({
            "stage": "spanner_query_error",
            "input": user_prompt,
            "error": str(e)
        }), exc_info=True)
        return []

async def extract_triple_from_prompt(user_prompt: str) -> Tuple[str, str, str]:
    prompt = f"""
다음 문장을 (	
subject,predicate,object) triple로 분해해줘.
형식: subject=..., predicate=..., object=...

문장: "{user_prompt}"
"""
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0}
    }

    response = await _call_vertex_api(payload)
    text = response["candidates"][0]["content"]["parts"][0]["text"]

    # 정규표현식으로 추출
    match = re.search(r"subject\s*=\s*(.+?),\s*predicate\s*=\s*(.+?),\s*object\s*=\s*(.*)", text)
    if match:
        return match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
    else:
        raise ValueError("Triple 추출 실패: " + text)




async def _build_vertex_payload(
    user_prompt: str,
    conversation_history: List[Dict[str, Any]],
    image_file: Optional[UploadFile],
    preloaded_triples: Optional[List[str]] = None
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    user_content_parts = []
    if image_file:
        image_base64 = base64.b64encode(await image_file.read()).decode('utf-8')
        user_content_parts.append({"inlineData": {"mimeType": image_file.content_type, "data": image_base64}})

    if user_prompt:
        user_content_parts.append({"text": user_prompt})

    current_contents = conversation_history + [{"role": "user", "parts": user_content_parts}]

    # 🧠 Triple grounding: 미리 받아온 게 있으면 쓰고, 없으면 추출
    if preloaded_triples is not None:
        triples = preloaded_triples
    else:
        try:
            subject, predicate, object_ = await extract_triple_from_prompt(user_prompt)
            triples = query_spanner_by_triple(subject, predicate, object_)
        except Exception as e:
            logger.warning(f"Triple 추출 또는 검색 실패: {e}")
            triples = []

    # 📎 grounding 내용 system prompt 앞에 삽입
    if triples:
        triple_text = "\n".join(triples)
        current_contents.insert(0, {
            "role": "user",
            "parts": [{"text": f"[Spanner Triple Grounding]\n{triple_text}"}]
        })

    payload = {
        "systemInstruction": {"parts": [{"text": Config.SYSTEM_INSTRUCTION}]},
        "contents": current_contents,
        "tools": [{"retrieval": {"vertexAiSearch": {"datastore": Config.DATASTORE_PATH}}}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 8192,
            "topP": 0.3
        }
    }

    return payload, current_contents


async def _call_vertex_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not credentials:
        raise ConnectionAbortedError("Server authentication is not configured.")

    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)

    headers = {
        'Authorization': f'Bearer {credentials.token}',
        'Content-Type': 'application/json; charset=utf-8'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(Config.MODEL_ENDPOINT_URL, headers=headers, json=payload, timeout=300) as response:
            if not response.ok:
                error_body = await response.text()
                raise VertexAIAPIError(f"HTTP error {response.status}", response.status, error_body)
            return await response.json()


async def _build_triple_only_payload(user_prompt: str, triples: List[str]) -> Dict[str, Any]:
    triple_text = "\n".join(triples) if triples else "관련된 triple 정보를 찾을 수 없습니다."
    instruction = f"""당신은 사용자의 질문에 대해 제공된 triple 정보만으로 답변을 작성하는 AI입니다.
아래는 triple 정보입니다:
{triple_text}
사용자 질문: {user_prompt}"""
    payload = {
        "contents": [{"role": "user", "parts": [{"text": instruction}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 8192, "topP": 0.8}
    }
    return payload

async def _build_summary_payload(triple_answer: str, vertex_answer: str, user_prompt: str) -> Dict[str, Any]:
    summary_prompt = f"""사용자의 질문: {user_prompt}

[Spanner Triple 기반 응답]
{triple_answer}

[Vertex AI Search 기반 응답]
{vertex_answer}

위 두 응답을 참고하여 최종 요약 응답을 생성하세요."""
    return {
        "contents": [{"role": "user", "parts": [{"text": summary_prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 8192, "topP": 0.8}
    }

@app.post('/api/generate')
async def generate_content(userPrompt: str = Form(""), conversationHistory: str = Form("[]"), imageFile: Optional[UploadFile] = File(None)):
    if not credentials:
        raise HTTPException(status_code=503, detail="서버 인증 실패")

    try:
        conversation_history = json.loads(conversationHistory)

        triples = query_spanner_triples(userPrompt)

        triple_payload = await _build_triple_only_payload(userPrompt, triples)
        triple_result = await _call_vertex_api(triple_payload)
        triple_text = triple_result['candidates'][0]['content']['parts'][0]['text']

        # ⬇ triple을 두 번째 쿼리로 넘김
        full_payload, full_history = await _build_vertex_payload(userPrompt, conversation_history, imageFile, preloaded_triples=triples)


        # 🔹 Step 1: Triple 기반 응답
        triple_payload = await _build_triple_only_payload(userPrompt, triples)
        triple_result = await _call_vertex_api(triple_payload)
        triple_text = triple_result['candidates'][0]['content']['parts'][0]['text']
        
        logger.info(json.dumps({
            "stage": "triple_answer_generated",
            "triple_input": userPrompt,
            "triples_used": triples,
            "triple_answer": triple_text
        }, ensure_ascii=False))

        # 🔹 Step 2: Vertex AI Search 기반 응답
        full_payload, full_history = await _build_vertex_payload(userPrompt, conversation_history, imageFile)
        vertex_result = await _call_vertex_api(full_payload)
        vertex_text = vertex_result['candidates'][0]['content']['parts'][0]['text']

        logger.info(json.dumps({
            "stage": "vertex_answer_generated",
            "vertex_input": userPrompt,
            "vertex_answer": vertex_text
        }, ensure_ascii=False))

        # 🔹 Step 3: 두 응답을 통합 요약
        summary_payload = await _build_summary_payload(triple_text, vertex_text, userPrompt)
        summary_result = await _call_vertex_api(summary_payload)
        summary_text = summary_result['candidates'][0]['content']['parts'][0]['text']

        logger.info(json.dumps({
            "stage": "summary_answer_generated",
            "user_prompt": userPrompt,
            "summary_answer": summary_text
        }, ensure_ascii=False))

        return JSONResponse({
            "triple_answer": triple_text,
            "vertex_answer": vertex_text,
            "summary_answer": summary_text,
            "updatedHistory": full_history
        })

    except Exception as e:
        logger.exception("예상치 못한 오류")
        raise HTTPException(status_code=500, detail=str(e))


    except Exception as e:
        logger.exception("예상치 못한 오류")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gcs/{bucket_name}/{file_path:path}")
async def proxy_gcs_file(bucket_name: str, file_path: str):
    if not storage_client:
        raise HTTPException(status_code=503, detail="스토리지 인증 실패")

    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        if not blob.exists():
            raise HTTPException(status_code=404, detail="파일 없음")

        def iterfile():
            with blob.open("rb") as f:
                yield from f

        content_type, _ = mimetypes.guess_type(file_path)
        content_type = content_type or "application/octet-stream"
        headers = {'Content-Disposition': f'inline; filename="{os.path.basename(file_path)}"'}
        return StreamingResponse(iterfile(), media_type=content_type, headers=headers)
    except Exception as e:
        logger.error("GCS 프록시 오류", exc_info=True)
        raise HTTPException(status_code=500, detail="파일 읽기 실패")

@app.get("/")
async def serve_root():
    return FileResponse("public/index.html")

app.mount("/", StaticFiles(directory="public"), name="static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api") or os.path.exists(os.path.join("public", full_path)):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse("public/index.html")
