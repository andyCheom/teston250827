import os
import json
import base64
import logging
import re
import mimetypes
import asyncio
import hashlib
from functools import lru_cache
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

# 메모리 캐시 (간단한 구현)
class MemoryCache:
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        
    def get(self, key: str):
        return self.cache.get(key)
        
    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        if len(self.cache) >= self.max_size:
            # LRU 방식으로 가장 오래된 항목 제거
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        import time
        self.cache[key] = {
            'value': value,
            'expires': time.time() + ttl_seconds
        }
    
    def is_valid(self, key: str) -> bool:
        import time
        if key not in self.cache:
            return False
        return time.time() < self.cache[key]['expires']

memory_cache = MemoryCache()

# DB 연결 풀링 
@lru_cache(maxsize=1)
def get_database_connection():
    """Spanner 데이터베이스 연결을 캐시하여 재사용"""
    instance = spanner_client.instance(Config.SPANNER_INSTANCE_ID)
    return instance.database(Config.SPANNER_DATABASE_ID)

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

def get_cache_key(prefix: str, *args) -> str:
    """캐시 키 생성"""
    combined = f"{prefix}:{'|'.join(str(arg) for arg in args)}"
    return hashlib.md5(combined.encode()).hexdigest()

def query_spanner_triples(user_prompt: str) -> List[str]:
    # 캐시 확인
    cache_key = get_cache_key("spanner_triples", user_prompt)
    if memory_cache.is_valid(cache_key):
        cached_result = memory_cache.get(cache_key)['value']
        logger.info(f"캐시에서 Triple 검색 결과 반환: {len(cached_result)}건")
        return cached_result
    
    try:
        logger.info(json.dumps({
            "stage": "spanner_query_start",
            "input": user_prompt
        }))

        database = get_database_connection()
        
        # 키워드 분해하여 더 정확한 검색
        keywords = user_prompt.split()
        conditions = []
        params = {}
        param_types = {}
        
        for i, keyword in enumerate(keywords):
            param_name = f"keyword_{i}"
            conditions.extend([
                f"LOWER(subject) LIKE @{param_name}",
                f"LOWER(predicate) LIKE @{param_name}",
                f"LOWER(object) LIKE @{param_name}"
            ])
            params[param_name] = f"%{keyword.lower()}%"
            param_types[param_name] = spanner.param_types.STRING
        
        where_clause = " OR ".join(conditions) if conditions else "1=1"
        query = f"""
        SELECT subject, predicate, object FROM `{Config.SPANNER_TABLE_NAME}`
        WHERE {where_clause}
        LIMIT 50
        """

        with database.snapshot() as snapshot:
            results = snapshot.execute_sql(query, params=params, param_types=param_types)
            triples = [f"{row[0]} {row[1]} {row[2]}" for row in results]

        logger.info(json.dumps({
            "stage": "spanner_query_success",
            "input": user_prompt,
            "result_count": len(triples),
            "results": triples
        }))

        # 결과 캐시 저장 (1시간)
        memory_cache.set(cache_key, triples, 3600)
        
        return triples

    except Exception as e:
        logger.error(json.dumps({
            "stage": "spanner_query_error",
            "input": user_prompt,
            "error": str(e)
        }), exc_info=True)
        return []

def query_spanner_by_triple(subject: str, predicate: str, object_: str) -> List[str]:
    try:
        logger.info(json.dumps({
            "stage": "spanner_triple_query_start",
            "subject": subject,
            "predicate": predicate,
            "object": object_
        }))

        database = get_database_connection()
        
        # 각 triple 요소에 대해 유연한 검색
        conditions = []
        params = {}
        param_types = {}
        
        if subject and subject.strip():
            conditions.append("LOWER(subject) LIKE @subject_param")
            params["subject_param"] = f"%{subject.lower().strip()}%"
            param_types["subject_param"] = spanner.param_types.STRING
            
        if predicate and predicate.strip():
            conditions.append("LOWER(predicate) LIKE @predicate_param")
            params["predicate_param"] = f"%{predicate.lower().strip()}%"
            param_types["predicate_param"] = spanner.param_types.STRING
            
        if object_ and object_.strip():
            conditions.append("LOWER(object) LIKE @object_param")
            params["object_param"] = f"%{object_.lower().strip()}%"
            param_types["object_param"] = spanner.param_types.STRING
        
        if not conditions:
            logger.warning("모든 triple 요소가 비어있음")
            return []
            
        where_clause = " OR ".join(conditions)
        query = f"""
        SELECT subject, predicate, object FROM `{Config.SPANNER_TABLE_NAME}`
        WHERE {where_clause}
        LIMIT 30
        """

        with database.snapshot() as snapshot:
            results = snapshot.execute_sql(query, params=params, param_types=param_types)
            triples = [f"{row[0]} {row[1]} {row[2]}" for row in results]

        logger.info(json.dumps({
            "stage": "spanner_triple_query_success",
            "subject": subject,
            "predicate": predicate,
            "object": object_,
            "result_count": len(triples),
            "results": triples
        }))

        return triples

    except Exception as e:
        logger.error(json.dumps({
            "stage": "spanner_triple_query_error",
            "subject": subject,
            "predicate": predicate,
            "object": object_,
            "error": str(e)
        }), exc_info=True)
        return []

async def extract_triple_from_prompt(user_prompt: str) -> Tuple[str, str, str]:
    prompt = f"""
사용자 질문을 분석하여 핵심 키워드를 (subject, predicate, object) triple로 추출해줘.

질문: "{user_prompt}"

추출 규칙:
- subject: 질문의 주요 대상 (제품명, 기능명 등)
- predicate: 관계나 동작 (사용법, 설정, 문제해결 등)  
- object: 구체적 속성이나 결과

응답 형식: subject=..., predicate=..., object=...

"""
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200}
    }

    response = await _call_vertex_api(payload)
    text = response["candidates"][0]["content"]["parts"][0]["text"]

    # 정규표현식으로 추출
    match = re.search(r"subject\s*=\s*(.+?),\s*predicate\s*=\s*(.+?),\s*object\s*=\s*(.*)", text)
    if match:
        subject = match.group(1).strip()
        predicate = match.group(2).strip() 
        object_ = match.group(3).strip()
        
        # 무관한 질문 체크
        if subject == "IRRELEVANT":
            raise ValueError("질문이 처음서비스와 무관함")
            
        return subject, predicate, object_
    else:
        raise ValueError("Triple 추출 실패: " + text)

async def validate_response_relevance(user_prompt: str, response: str) -> bool:
    """응답이 질문과 연관성이 있는지 검증"""
    validation_prompt = f"""
사용자 질문: "{user_prompt}"
AI 응답: "{response[:500]}..."

위 응답이 질문에 적절히 답하고 있는지 판단해줘.

판단 기준:
1. 질문의 핵심 의도에 부합하는가?
2. 구체적이고 유용한 정보를 제공하는가?
3. "죄송합니다", "답변드릴 수 없습니다" 같은 회피 답변이 아닌가?

응답: YES 또는 NO
"""
    
    payload = {
        "contents": [{"role": "user", "parts": [{"text": validation_prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 10}
    }
    
    try:
        response = await _call_vertex_api(payload)
        result = response["candidates"][0]["content"]["parts"][0]["text"].strip()
        return result.upper() == "YES"
    except:
        return True  # 검증 실패 시 기본적으로 통과




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


# 공통 세션과 헤더 캐싱
_shared_session = None
_cached_headers = None
_headers_cache_time = 0

async def get_shared_session():
    global _shared_session
    if _shared_session is None or _shared_session.closed:
        # 연결 풀 최적화 설정
        connector = aiohttp.TCPConnector(
            limit=100,  # 최대 연결 수
            limit_per_host=20,  # 호스트당 최대 연결 수
            keepalive_timeout=30,  # Keep-alive 타임아웃
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=300, connect=10)
        _shared_session = aiohttp.ClientSession(connector=connector, timeout=timeout)
    return _shared_session

async def get_cached_headers():
    global _cached_headers, _headers_cache_time
    import time
    
    # 헤더를 5분간 캐시
    if _cached_headers is None or time.time() - _headers_cache_time > 300:
        if not credentials:
            raise ConnectionAbortedError("Server authentication is not configured.")
        
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        
        _cached_headers = {
            'Authorization': f'Bearer {credentials.token}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        _headers_cache_time = time.time()
    
    return _cached_headers

async def _call_vertex_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    session = await get_shared_session()
    headers = await get_cached_headers()

    async with session.post(Config.MODEL_ENDPOINT_URL, headers=headers, json=payload) as response:
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

위 두 응답을 참고하여 최종 응답을 생성하세요."""
    return {
        "contents": [{"role": "user", "parts": [{"text": summary_prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 16192, "topP": 0.8}
    }

@app.post('/api/generate')
async def generate_content(userPrompt: str = Form(""), conversationHistory: str = Form("[]"), imageFile: Optional[UploadFile] = File(None)):
    if not credentials:
        raise HTTPException(status_code=503, detail="서버 인증 실패")

    try:
        conversation_history = json.loads(conversationHistory)

        # 🔹 Step 1: Triple 검색 및 기반 응답
        triples = query_spanner_triples(userPrompt)
        
        # Triple이 없으면 추출하여 다시 검색 시도
        if not triples:
            try:
                subject, predicate, object_ = await extract_triple_from_prompt(userPrompt)
                triples = query_spanner_by_triple(subject, predicate, object_)
                logger.info(f"Fallback triple 검색 결과: {len(triples)}건")
            except Exception as e:
                logger.warning(f"Fallback triple 검색 실패: {e}")

        # 🚀 Step 1&2: Triple 기반 응답과 Vertex AI 검색을 병렬 처리
        triple_payload = await _build_triple_only_payload(userPrompt, triples)
        full_payload, full_history = await _build_vertex_payload(userPrompt, conversation_history, imageFile, preloaded_triples=triples)
        
        # 병렬 API 호출로 속도 2배 향상
        triple_task = asyncio.create_task(_call_vertex_api(triple_payload))
        vertex_task = asyncio.create_task(_call_vertex_api(full_payload))
        
        triple_result, vertex_result = await asyncio.gather(triple_task, vertex_task)
        
        triple_text = triple_result['candidates'][0]['content']['parts'][0]['text']
        vertex_text = vertex_result['candidates'][0]['content']['parts'][0]['text']
        
        logger.info(json.dumps({
            "stage": "parallel_answers_generated",
            "triple_input": userPrompt,
            "triples_used": triples,
            "triple_answer_length": len(triple_text),
            "vertex_answer_length": len(vertex_text)
        }, ensure_ascii=False))

        # 🔹 Step 3&4: 요약과 검증을 병렬 처리
        summary_payload = await _build_summary_payload(triple_text, vertex_text, userPrompt)
        
        summary_task = asyncio.create_task(_call_vertex_api(summary_payload))
        validation_task = asyncio.create_task(validate_response_relevance(userPrompt, f"{triple_text[:300]}..."))
        
        summary_result, is_relevant_preview = await asyncio.gather(summary_task, validation_task)
        summary_text = summary_result['candidates'][0]['content']['parts'][0]['text']
        
        # 최종 검증 (요약 결과 기준)
        is_relevant = await validate_response_relevance(userPrompt, summary_text) if not is_relevant_preview else True
        
        if not is_relevant:
            logger.warning(f"응답 연관성 검증 실패 - 질문: {userPrompt}")
            # 처음서비스와 무관한 질문에 대한 표준 응답
            summary_text = f"""죄송하지만, **"{userPrompt}"**에 대한 정보는 현재 제공해드리기 어렵습니다.

**처음서비스**의 제품 및 서비스에 관한 구체적인 질문을 해주시면, 더 정확하고 유용한 답변을 드릴 수 있습니다.

예를 들어:
- 특정 기능의 사용 방법
- 설정 및 구성 관련 문의  
- 문제 해결 방법
- 서비스 이용 가이드

추가 도움이 필요하시면 언제든 문의해 주세요! 😊"""

        logger.info(json.dumps({
            "stage": "summary_answer_generated",
            "user_prompt": userPrompt,
            "is_relevant": is_relevant,
            "summary_answer": summary_text[:200] + "..." if len(summary_text) > 200 else summary_text
        }, ensure_ascii=False))

        return JSONResponse({
            "triple_answer": triple_text,
            "vertex_answer": vertex_text,
            "summary_answer": summary_text,
            "updatedHistory": full_history,
            "quality_check": {
                "relevance_passed": is_relevant,
                "triples_found": len(triples) > 0
            }
        })

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