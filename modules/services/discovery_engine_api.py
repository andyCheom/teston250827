"""Discovery Engine Answer API 서비스"""
import time
import logging
from typing import Dict, Any, Optional
import aiohttp
import json

from ..config import Config
from ..auth import get_credentials
import google.auth
import google.auth.transport.requests

logger = logging.getLogger(__name__)

# Discovery Engine API 설정
DISCOVERY_BASE_URL = "https://discoveryengine.googleapis.com/v1alpha"

# 공유 세션 캐싱
_discovery_session = None
_discovery_headers = None
_discovery_headers_cache_time = 0

class DiscoveryEngineAPIError(Exception):
    """Discovery Engine API 호출 오류"""
    def __init__(self, message: str, status_code: int, error_body: str):
        super().__init__(message)
        self.status_code = status_code
        self.error_body = error_body

async def get_discovery_session():
    """Discovery Engine용 공유 HTTP 세션 관리"""
    global _discovery_session
    if _discovery_session is None or _discovery_session.closed:
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=10,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=300, connect=10)
        _discovery_session = aiohttp.ClientSession(connector=connector, timeout=timeout)
    return _discovery_session

async def get_discovery_headers():
    """Discovery Engine용 인증 헤더 캐싱"""
    global _discovery_headers, _discovery_headers_cache_time
    
    # 헤더를 5분간 캐시
    if _discovery_headers is None or time.time() - _discovery_headers_cache_time > 300:
        try:
            credentials = get_credentials()
            if not credentials:
                raise ConnectionAbortedError("Server authentication is not configured.")
            
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            
            _discovery_headers = {
                'Authorization': f'Bearer {credentials.token}',
                'Content-Type': 'application/json'
            }
            _discovery_headers_cache_time = time.time()
            
            logger.info("Discovery Engine 인증 헤더 생성 완료")
            
        except Exception as e:
            logger.error(f"Discovery Engine 인증 헤더 생성 실패: {e}")
            raise ConnectionAbortedError(f"Discovery Engine authentication failed: {e}")
    
    return _discovery_headers

async def search_documents(query: str) -> Dict[str, Any]:
    """Discovery Engine 검색 API 호출"""
    session = await get_discovery_session()
    headers = await get_discovery_headers()
    
    # Config에서 동적으로 가져오기
    project_id = Config.PROJECT_ID
    location = Config.DISCOVERY_LOCATION
    collection = Config.DISCOVERY_COLLECTION
    engine_id = Config.DISCOVERY_ENGINE_ID
    serving_config = Config.DISCOVERY_SERVING_CONFIG
    
    url = f"{DISCOVERY_BASE_URL}/projects/{project_id}/locations/{location}/collections/{collection}/engines/{engine_id}/servingConfigs/{serving_config}:search"
    
    payload = {
        "query": query,
        "pageSize": 10,
        "session": f"projects/{project_id}/locations/{location}/collections/{collection}/engines/{engine_id}/sessions/-",
        "spellCorrectionSpec": {"mode": "AUTO"},
        "languageCode": "ko",
        "userInfo": {"timeZone": "Asia/Seoul"},
        "contentSearchSpec": {"snippetSpec": {"returnSnippet": True}}
    }
    
    logger.info(f"Discovery Engine Search 요청: {url}")
    logger.info(f"Query: {query}")
    
    async with session.post(url, headers=headers, json=payload) as response:
        if not response.ok:
            error_body = await response.text()
            logger.error(f"Discovery Engine Search 실패: {response.status} - {error_body}")
            raise DiscoveryEngineAPIError(f"Search API error {response.status}", response.status, error_body)
        
        result = await response.json()
        logger.info(f"Discovery Engine Search 성공: {len(result.get('results', []))}건 검색됨")
        return result

async def generate_answer(query: str, query_id: str, session_id: str) -> Dict[str, Any]:
    """Discovery Engine Answer API 호출"""
    session = await get_discovery_session()
    headers = await get_discovery_headers()
    
    # Config에서 동적으로 가져오기
    project_id = Config.PROJECT_ID
    location = Config.DISCOVERY_LOCATION
    collection = Config.DISCOVERY_COLLECTION
    engine_id = Config.DISCOVERY_ENGINE_ID
    serving_config = Config.DISCOVERY_SERVING_CONFIG
    
    url = f"{DISCOVERY_BASE_URL}/projects/{project_id}/locations/{location}/collections/{collection}/engines/{engine_id}/servingConfigs/{serving_config}:answer"
    
    # 프롬프트 로드
    system_prompt = Config.load_system_instruction()
    
    payload = {
        "query": {
            "text": query,
            "queryId": query_id
        },
        "session": session_id,
        "relatedQuestionsSpec": {"enable": True},
        "answerGenerationSpec": {
            "ignoreAdversarialQuery": False,
            "ignoreNonAnswerSeekingQuery": False,
            "ignoreLowRelevantContent": False,  # 더 많은 콘텐츠 포함
            "multimodalSpec": {"imageSource": "CORPUS_IMAGE_ONLY"},
            "includeCitations": True,
            "promptSpec": {"preamble": system_prompt},
            "modelSpec": {"modelVersion": "gemini-2.5-flash/answer_gen/v1"}
        }
    }
    
    async with session.post(url, headers=headers, json=payload) as response:
        if not response.ok:
            error_body = await response.text()
            raise DiscoveryEngineAPIError(f"Answer API error {response.status}", response.status, error_body)
        return await response.json()


async def get_complete_discovery_answer(user_query: str, image_file=None) -> Dict[str, Any]:
    """Discovery Engine을 통한 완전한 답변 생성 플로우"""
    try:
        # 이미지 업로드가 있어도 무시하고 텍스트 쿼리만 사용
        final_query = user_query
        
        logger.info(f"Discovery Engine 검색 시작: {final_query[:100]}...")
        
        # 1. Search API 호출
        search_result = await search_documents(final_query)
        
        # Query ID와 Session ID 추출
        query_id = search_result.get("sessionInfo", {}).get("queryId")
        session_id = search_result.get("sessionInfo", {}).get("name")
        
        logger.info(f"Discovery Engine 검색 완료 - Query ID: {query_id}")
        logger.info(f"검색 결과 개수: {len(search_result.get('results', []))}")
        logger.debug(f"전체 검색 결과: {search_result}")
        
        # 2. Answer API 호출 (선택적)
        answer_text = ""
        citations = []
        related_questions = []
        
        if query_id and session_id:
            try:
                logger.info(f"Answer API 호출 시작 - Query ID: {query_id}, Session ID: {session_id}")
                answer_result = await generate_answer(final_query, query_id, session_id)
                logger.info(f"Answer API 응답 받음")
                
                # 응답 구조 전체 로깅
                logger.debug(f"전체 Answer API 응답: {answer_result}")
                
                # 응답 파싱
                if answer_result.get("answer", {}).get("answerText"):
                    answer_text = answer_result["answer"]["answerText"]
                    logger.info(f"Answer text 추출 성공: {len(answer_text)}자")
                else:
                    logger.warning("Answer API 응답에 answerText가 없음")
                
                if answer_result.get("answer", {}).get("citations"):
                    citations = answer_result["answer"]["citations"]
                    logger.info(f"Citations 발견: {len(citations)}개")
                    for i, citation in enumerate(citations):
                        logger.info(f"Citation {i+1}: title={citation.get('title', 'N/A')}, uri={citation.get('uri', 'N/A')}")
                else:
                    logger.warning("Answer API 응답에 citations가 없음")
                
                if answer_result.get("relatedQuestions"):
                    # Discovery Engine의 relatedQuestions를 문자열 배열로 변환
                    related_questions = answer_result["relatedQuestions"]
                    logger.info(f"Related questions 발견: {len(related_questions)}개")
                    logger.info(f"Related questions 내용: {related_questions}")
                else:
                    logger.info("Related questions 없음")
                
                logger.info(f"Discovery Engine 답변 생성 완료 - 길이: {len(answer_text)}")
                
            except Exception as e:
                logger.error(f"Answer API 실패, 검색 결과만 사용: {e}", exc_info=True)
                # Answer API 실패 시 검색 결과로 대체
                search_results = search_result.get("results", [])
                if search_results:
                    answer_text = "Discovery Engine 검색 결과를 바탕으로 한 답변입니다:\n\n"
                    for i, result in enumerate(search_results[:3], 1):
                        snippet = result.get("document", {}).get("derivedStructData", {}).get("snippets", [])
                        if snippet:
                            answer_text += f"{i}. {snippet[0].get('snippet', '내용 없음')}\n\n"
        else:
            logger.warning("Query ID 또는 Session ID 추출 실패 - 검색 결과만 사용")
            # Query ID 추출 실패 시 검색 결과로 대체
            search_results = search_result.get("results", [])
            if search_results:
                answer_text = "검색 결과를 바탕으로 한 답변입니다:\n\n"
                for i, result in enumerate(search_results[:3], 1):
                    snippet = result.get("document", {}).get("derivedStructData", {}).get("snippets", [])
                    if snippet:
                        answer_text += f"{i}. {snippet[0].get('snippet', '내용 없음')}\n\n"
            else:
                answer_text = "검색 결과를 찾을 수 없습니다."
        
        # Citations가 비어있고 search_results가 있는 경우, search_results에서 citations 생성
        if not citations and search_result.get("results", []):
            logger.info("Answer API citations가 없어서 Search Results에서 citations 생성")
            citations = []
            for i, result in enumerate(search_result.get("results", [])[:5]):  # 최대 5개
                doc = result.get("document", {})
                derived_data = doc.get("derivedStructData", {})
                
                title = derived_data.get("title", f"문서 {i+1}")
                uri = derived_data.get("link") or doc.get("uri", "")
                
                if uri:  # URI가 있는 경우만 citation으로 추가
                    citations.append({
                        "title": title,
                        "uri": uri,
                        "displayName": title
                    })
                    logger.info(f"Search Result에서 Citation 생성: {title} -> {uri}")
            
            logger.info(f"Search Results에서 생성된 Citations: {len(citations)}개")
        
        # 최종 결과 로깅
        logger.info(f"최종 답변 상태 - answer_text 길이: {len(answer_text)}, citations: {len(citations)}개")
        logger.info(f"Citations 요약: {[{'title': c.get('title', ''), 'has_uri': bool(c.get('uri'))} for c in citations]}")
        
        result = {
            "answer_text": answer_text,
            "citations": citations,
            "search_results": search_result.get("results", []),
            "related_questions": related_questions,
            "query_id": query_id or "",
            "session_id": session_id or "",
            "final_query_used": final_query
        }
        
        # 빈 답변 경고
        if not answer_text or answer_text.strip() == "":
            logger.warning("빈 답변이 반환됨 - 검색 결과를 확인하세요")
            logger.debug(f"검색 결과: {search_result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Discovery Engine 답변 생성 실패: {e}")
        raise