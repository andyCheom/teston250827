import os
import json
import base64
import logging
import re
import mimetypes
import asyncio
import time
from typing import Dict, Any, List, Tuple, Optional, Callable
from functools import wraps
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import google.auth
import google.auth.transport.requests
from google.cloud import storage, spanner, secretmanager
import requests, markdown
from requests import exceptions as requests_exceptions
from dotenv import load_dotenv
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2 import service_account
import aiohttp

app = FastAPI(static_files_directory="public", title="Gemini RAG Chatbot API", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 연결 초기화"""
    logger.info("🚀 애플리케이션 시작 - 클라이언트 연결 초기화")
    initialize_clients()

@app.on_event("shutdown") 
async def shutdown_event():
    """앱 종료 시 연결 정리"""
    logger.info("🔄 애플리케이션 종료 - 연결 정리")
    global spanner_client
    if spanner_client:
        spanner_client.close()
load_dotenv()

class Config:
    @staticmethod
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

    @staticmethod
    def get_system_instruction():
        try:
            with open(Config.SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"System prompt file not found: {Config.SYSTEM_PROMPT_PATH}")
            return "You are a helpful AI assistant."
        except Exception as e:
            logger.error(f"Error reading system prompt file: {e}")
            return "You are a helpful AI assistant."

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SERVICE_ACCOUNT_PATH = "keys/cheom-kdb-test1-faf5cf87a1fd.json"

def get_service_account_credentials():
    """Secret Manager 또는 로컬 파일에서 서비스 계정 인증 정보 가져오기"""
    use_secret_manager = os.environ.get("USE_SECRET_MANAGER", "false").lower() == "true"
    
    if use_secret_manager:
        try:
            # Secret Manager에서 서비스 계정 JSON 가져오기
            service_account_json = os.environ.get("SERVICE_ACCOUNT_JSON")
            if service_account_json:
                # 환경변수에서 직접 JSON 문자열 사용 (Cloud Run secrets)
                credentials_info = json.loads(service_account_json)
                return service_account.Credentials.from_service_account_info(
                    credentials_info,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            else:
                # Secret Manager API를 사용하여 직접 가져오기
                project_id = os.environ.get("PROJECT_ID", "cheom-kdb-test1")
                secret_name = f"projects/{project_id}/secrets/service-account-key/versions/latest"
                
                # 기본 인증으로 Secret Manager 클라이언트 생성
                client = secretmanager.SecretManagerServiceClient()
                response = client.access_secret_version(request={"name": secret_name})
                secret_value = response.payload.data.decode("UTF-8")
                
                credentials_info = json.loads(secret_value)
                return service_account.Credentials.from_service_account_info(
                    credentials_info,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
        except Exception as e:
            logger.warning(f"Secret Manager에서 인증 정보 가져오기 실패: {e}, 기본 인증 사용")
            return None
    else:
        # 로컬 파일 사용
        if os.path.exists(SERVICE_ACCOUNT_PATH):
            return service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_PATH,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
    
    return None

# 전역 클라이언트 및 데이터베이스 객체
credentials = None
storage_client = None
spanner_client = None
spanner_database = None

def initialize_clients():
    """클라이언트 초기화 및 연결 풀 설정"""
    global credentials, storage_client, spanner_client, spanner_database
    
    try:
        # Secret Manager 또는 로컬 파일에서 인증 정보 가져오기
        credentials = get_service_account_credentials()
        
        if credentials:
            project_id = credentials.project_id
            logger.info(f"✅ 서비스 계정 인증 성공 - project_id: {project_id}")
        else:
            # 기본 인증 사용 (Cloud Run 환경에서)
            credentials, project_id = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            logger.info(f"✅ 기본 인증 사용 - project_id: {project_id}")
        
        # Storage 클라이언트
        storage_client = storage.Client(credentials=credentials, project=project_id)
        
        # Spanner 클라이언트 (연결 풀 설정)
        spanner_client = spanner.Client(
            credentials=credentials, 
            project=project_id
        )
        
        # 데이터베이스 객체 미리 생성 (재사용)
        instance = spanner_client.instance(Config.SPANNER_INSTANCE_ID)
        spanner_database = instance.database(Config.SPANNER_DATABASE_ID)
        
        logger.info(f"✅ 인증 및 연결 풀 초기화 완료 - project_id: {project_id}")
        
    except Exception as e:
        logger.critical("❌ 인증 또는 연결 풀 초기화 오류", exc_info=True)
        credentials = None
        storage_client = None
        spanner_client = None
        spanner_database = None

# 클라이언트 초기화 실행
initialize_clients()

# === 커스텀 예외 클래스 ===
class VertexAIAPIError(Exception):
    def __init__(self, message: str, status_code: int, error_body: str):
        super().__init__(message)
        self.status_code = status_code
        self.error_body = error_body

class SpannerConnectionError(Exception):
    """Spanner 연결 관련 오류"""
    pass

class TripleExtractionError(Exception):
    """Triple 추출 관련 오류"""
    pass

class DocumentProcessingError(Exception):
    """문서 처리 관련 오류"""
    pass

# === 재시도 데코레이터 ===
def retry_async(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, 
               exceptions: tuple = (Exception,)):
    """비동기 함수용 재시도 데코레이터"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        break
                    
                    wait_time = delay * (backoff ** attempt)
                    logger.warning(f"함수 {func.__name__} 재시도 {attempt + 1}/{max_attempts} "
                                 f"(다음 시도까지 {wait_time:.1f}초 대기): {str(e)}")
                    await asyncio.sleep(wait_time)
            
            # 모든 재시도 실패
            logger.error(f"함수 {func.__name__} {max_attempts}회 재시도 모두 실패")
            raise last_exception
            
        return wrapper
    return decorator

# === Circuit Breaker 패턴 ===
class CircuitBreaker:
    """Circuit Breaker 패턴 구현"""
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if time.time() - self.last_failure_time < self.timeout:
                    raise HTTPException(
                        status_code=503, 
                        detail="서비스 일시적 이용 불가 (Circuit Breaker OPEN)"
                    )
                else:
                    self.state = "HALF_OPEN"
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                raise e
        
        return wrapper
    
    def _on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(f"Circuit Breaker OPEN - {self.failure_count}회 연속 실패")

# Circuit Breaker 인스턴스
vertex_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=30.0)
spanner_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60.0)

def extract_document_links(vertex_result: Dict[str, Any]) -> List[Dict[str, str]]:
    """Vertex AI Search 결과에서 문서 링크 정보를 추출"""
    links = []
    try:
        # groundingMetadata에서 문서 정보 추출
        if 'candidates' in vertex_result:
            candidate = vertex_result['candidates'][0]
            if 'groundingMetadata' in candidate:
                grounding_supports = candidate['groundingMetadata'].get('groundingSupports', [])
                
                for support in grounding_supports:
                    if 'segment' in support:
                        segment = support['segment']
                        if 'text' in segment and 'retrievalMetadata' in segment:
                            metadata = segment['retrievalMetadata']
                            if 'source' in metadata:
                                source = metadata['source']
                                # GCS 링크만 필터링
                                if source.startswith('gs://') or 'storage.googleapis.com' in source:
                                    # 파일명을 제목으로 추출
                                    title = source.split('/')[-1] if '/' in source else source
                                    title = title.replace('.pdf', '').replace('.txt', '').replace('.docx', '')
                                    
                                    links.append({
                                        'title': title,
                                        'url': source
                                    })
        
        # 중복 제거
        seen = set()
        unique_links = []
        for link in links:
            if link['url'] not in seen:
                seen.add(link['url'])
                unique_links.append(link)
                
        return unique_links[:5]  # 최대 5개까지만 반환
        
    except Exception as e:
        logger.warning(f"문서 링크 추출 실패: {e}")
        return []

def extract_keywords_from_prompt(user_prompt: str) -> List[str]:
    """사용자 프롬프트에서 핵심 키워드를 추출"""
    # 기본적인 불용어 제거 및 키워드 추출
    stop_words = {'은', '는', '이', '가', '을', '를', '의', '에', '에서', '로', '으로', '와', '과', '하다', '되다', '있다', '없다', '이다', '아니다', 
                  '무엇', '어떤', '어디', '언제', '왜', '어떻게', '누구', '몇', '얼마', '인가요', '입니까', '습니까', '나요', '까요', '는지', '인지'}
    
    # 특수문자 제거 및 단어 분리
    words = re.sub(r'[^\w\s]', ' ', user_prompt).split()
    
    # 불용어 제거 및 2글자 이상 단어만 추출
    keywords = [word for word in words if len(word) >= 2 and word not in stop_words]
    
    return keywords[:5]  # 최대 5개 키워드만 사용

@spanner_circuit_breaker
@retry_async(max_attempts=3, delay=1.0, exceptions=(SpannerConnectionError, Exception))
async def query_spanner_triples(user_prompt: str) -> List[str]:
    """최적화된 Spanner 트리플 쿼리 (연결 풀 사용)"""
    if not spanner_database:
        logger.error("Spanner 데이터베이스 연결이 초기화되지 않았습니다.")
        raise SpannerConnectionError("Spanner 데이터베이스 연결이 초기화되지 않았습니다")
        
    try:
        logger.info(json.dumps({
            "stage": "spanner_query_start",
            "input": user_prompt
        }))

        # 키워드 추출
        keywords = extract_keywords_from_prompt(user_prompt)
        
        logger.info(json.dumps({
            "stage": "keywords_extracted",
            "input": user_prompt,
            "keywords": keywords
        }))

        # 전역 데이터베이스 객체 재사용 (연결 풀 활용)
        
        all_triples = []
        
        # 1. 원본 프롬프트로 검색
        query = f"""
        SELECT subject, predicate, object FROM `{Config.SPANNER_TABLE_NAME}`
        WHERE subject LIKE @term OR predicate LIKE @term OR object LIKE @term
        LIMIT 10
        """
        params = {"term": f"%{user_prompt}%"}
        param_types = {"term": spanner.param_types.STRING}

        with spanner_database.snapshot() as snapshot:
            results = snapshot.execute_sql(query, params=params, param_types=param_types)
            original_triples = [f"{row[0]} {row[1]} {row[2]}" for row in results]
            all_triples.extend(original_triples)

        # 2. 키워드별로 검색 (중복 제거)
        for keyword in keywords:
            params = {"term": f"%{keyword}%"}
            with spanner_database.snapshot() as snapshot:
                results = snapshot.execute_sql(query, params=params, param_types=param_types)
                keyword_triples = [f"{row[0]} {row[1]} {row[2]}" for row in results]
                for triple in keyword_triples:
                    if triple not in all_triples:
                        all_triples.append(triple)
        
        # 최대 15개까지만 반환
        triples = all_triples[:15]

        logger.info(json.dumps({
            "stage": "spanner_query_success",
            "input": user_prompt,
            "keywords": keywords,
            "original_results": len(original_triples),
            "total_result_count": len(triples),
            "results": triples
        }))

        return triples

    except Exception as e:
        logger.error(json.dumps({
            "stage": "spanner_query_error",
            "input": user_prompt,
            "error": str(e),
            "error_type": type(e).__name__
        }), exc_info=True)
        
        # 구체적인 예외 유형에 따라 처리
        if "Connection" in str(e) or "timeout" in str(e).lower():
            raise SpannerConnectionError(f"Spanner 연결 오류: {str(e)}")
        else:
            raise TripleExtractionError(f"Triple 검색 중 오류: {str(e)}")

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
            triples = await query_spanner_triples(user_prompt)
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
        "systemInstruction": {"parts": [{"text": Config.get_system_instruction()}]},
        "contents": current_contents,
        "tools": [{"retrieval": {"vertexAiSearch": {"datastore": Config.DATASTORE_PATH}}}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 8192,
            "topP": 0.3
        }
    }

    return payload, current_contents


@vertex_circuit_breaker
@retry_async(max_attempts=3, delay=2.0, exceptions=(VertexAIAPIError, aiohttp.ClientError))
async def _call_vertex_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not credentials:
        raise VertexAIAPIError("인증 정보가 초기화되지 않았습니다", 500, "No credentials")

    try:
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)

        headers = {
            'Authorization': f'Bearer {credentials.token}',
            'Content-Type': 'application/json; charset=utf-8'
        }

        timeout = aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(Config.MODEL_ENDPOINT_URL, headers=headers, json=payload) as response:
                if not response.ok:
                    error_body = await response.text()
                    error_msg = f"Vertex AI API 호출 실패 (HTTP {response.status})"
                    
                    # 상태 코드별 상세 메시지
                    if response.status == 400:
                        error_msg += " - 잘못된 요청 형식"
                    elif response.status == 401:
                        error_msg += " - 인증 실패"
                    elif response.status == 403:
                        error_msg += " - 접근 권한 없음"
                    elif response.status == 429:
                        error_msg += " - 요청 한도 초과"
                    elif response.status >= 500:
                        error_msg += " - 서버 내부 오류"
                    
                    raise VertexAIAPIError(error_msg, response.status, error_body)
                
                try:
                    return await response.json()
                except aiohttp.ContentTypeError as e:
                    response_text = await response.text()
                    logger.error(f"Vertex AI API returned non-JSON response: {response_text[:500]}")
                    raise VertexAIAPIError(f"서버가 비정상적인 응답을 반환했습니다", response.status, response_text)
                except Exception as e:
                    response_text = await response.text()
                    logger.error(f"JSON parsing failed: {str(e)}, Response: {response_text[:500]}")
                    raise VertexAIAPIError(f"응답 파싱 실패: {str(e)}", response.status, response_text)
                
    except aiohttp.ClientError as e:
        logger.error(f"Vertex AI API 네트워크 오류: {str(e)}")
        raise VertexAIAPIError(f"네트워크 연결 오류: {str(e)}", 503, str(e))
    except Exception as e:
        logger.error(f"Vertex AI API 예상치 못한 오류: {str(e)}")
        raise VertexAIAPIError(f"예상치 못한 오류: {str(e)}", 500, str(e))



@app.post('/api/generate')
async def generate_content(userPrompt: str = Form(""), conversationHistory: str = Form("[]"), imageFile: Optional[UploadFile] = File(None)):
    if not credentials:
        raise HTTPException(status_code=503, detail="서버 인증 실패")

    try:
        conversation_history = json.loads(conversationHistory)

        # Triple 정보 조회
        triples = await query_spanner_triples(userPrompt)

        # 🚀 단일 API 호출로 Triple + Vertex AI Search 통합 처리
        payload, full_history = await _build_vertex_payload(userPrompt, conversation_history, imageFile, triples)
        result = await _call_vertex_api(payload)
        
        # 응답 텍스트 추출
        response_text = result['candidates'][0]['content']['parts'][0]['text']
        
        # RAG 문서 링크 추출
        document_links = extract_document_links(result)
        
        # 문서 링크를 응답에 추가
        if document_links:
            link_text = "\n\n👉 관련 문서 보기:\n"
            for link in document_links:
                link_text += f"- {link['title']}\n"
            response_text += link_text

        logger.info(json.dumps({
            "stage": "unified_answer_generated",
            "user_prompt": userPrompt,
            "triples_used": triples,
            "response": response_text,
            "document_links_count": len(document_links)
        }, ensure_ascii=False))

        return JSONResponse({
            "summary_answer": response_text,
            "document_links": document_links,
            "updatedHistory": full_history
        })

    except SpannerConnectionError as e:
        logger.error(f"Spanner 연결 오류: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail="데이터베이스 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )
    except TripleExtractionError as e:
        logger.warning(f"Triple 추출 오류 (서비스 계속): {str(e)}")
        # Triple 검색 실패해도 Vertex AI Search만으로 답변 시도
        try:
            payload, full_history = await _build_vertex_payload(userPrompt, conversation_history, imageFile, [])
            result = await _call_vertex_api(payload)
            response_text = result['candidates'][0]['content']['parts'][0]['text']
            
            return JSONResponse({
                "summary_answer": f"⚠️ 일부 정보 검색에 문제가 있었지만, 가능한 답변을 제공합니다.\n\n{response_text}",
                "document_links": extract_document_links(result),
                "updatedHistory": full_history
            })
        except Exception:
            raise HTTPException(
                status_code=503,
                detail="지식베이스 검색에 문제가 있어 답변을 생성할 수 없습니다."
            )
    except VertexAIAPIError as e:
        logger.error(f"Vertex AI API 오류: {str(e)}")
        if e.status_code == 429:
            raise HTTPException(
                status_code=429,
                detail="요청이 너무 많습니다. 잠시 후 다시 시도해주세요."
            )
        elif e.status_code >= 500:
            raise HTTPException(
                status_code=503,
                detail="AI 서비스에 일시적 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="요청 처리 중 문제가 발생했습니다. 입력을 확인해주세요."
            )
    except HTTPException:
        # HTTPException은 그대로 전달
        raise
    except Exception as e:
        logger.exception("예상치 못한 오류 발생")
        raise HTTPException(
            status_code=500,
            detail="서비스에 일시적 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
        )


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

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트 - 연결 상태 및 Circuit Breaker 상태 확인"""
    status = {
        "status": "healthy",
        "connections": {
            "spanner": spanner_database is not None,
            "storage": storage_client is not None,
            "credentials": credentials is not None
        },
        "circuit_breakers": {
            "vertex_ai": {
                "state": vertex_circuit_breaker.state,
                "failure_count": vertex_circuit_breaker.failure_count
            },
            "spanner": {
                "state": spanner_circuit_breaker.state,
                "failure_count": spanner_circuit_breaker.failure_count
            }
        }
    }
    
    # 연결 상태나 Circuit Breaker 상태 확인
    connections_healthy = all(status["connections"].values())
    circuit_breakers_healthy = all(
        cb["state"] == "CLOSED" for cb in status["circuit_breakers"].values()
    )
    
    if not connections_healthy or not circuit_breakers_healthy:
        status["status"] = "unhealthy"
        return JSONResponse(status_code=503, content=status)
    
    return JSONResponse(content=status)

@app.get("/")
async def serve_root():
    return FileResponse("public/index.html")

app.mount("/", StaticFiles(directory="public"), name="static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api") or os.path.exists(os.path.join("public", full_path)):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse("public/index.html")