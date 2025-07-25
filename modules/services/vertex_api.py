"""Discovery Engine API 호출 서비스"""
import logging
import hashlib
from typing import Dict, Any, Optional
from functools import lru_cache
from google.cloud import discoveryengine_v1 as discoveryengine

from ..config import Config
from ..auth import get_discovery_client

logger = logging.getLogger(__name__)

# Discovery Engine 설정
PROJECT_ID = "cheom-kdb-test1"
LOCATION = "global"
ENGINE_ID = "test_1753406039510"

# 응답 캐시 (메모리 기반)
_response_cache = {}

def _get_cache_key(query: str) -> str:
    """쿼리에서 캐시 키 생성"""
    return hashlib.md5(query.encode('utf-8')).hexdigest()

def _get_cached_response(query: str) -> Optional[Dict[str, Any]]:
    """캐시된 응답 반환"""
    cache_key = _get_cache_key(query)
    return _response_cache.get(cache_key)

def _cache_response(query: str, response: Dict[str, Any]) -> None:
    """응답을 캐시에 저장 (최대 100개, LRU)"""
    cache_key = _get_cache_key(query)
    
    # 캐시 크기 제한
    if len(_response_cache) >= 100:
        # 가장 오래된 항목 제거 (간단한 FIFO)
        oldest_key = next(iter(_response_cache))
        del _response_cache[oldest_key]
    
    _response_cache[cache_key] = response

class DiscoveryEngineAPIError(Exception):
    """Discovery Engine API 호출 오류"""
    def __init__(self, message: str, details: str = ""):
        super().__init__(message)
        self.details = details

def _truncate_query(query: str, max_length: int = 2000) -> str:
    """쿼리를 최대 길이로 자르기"""
    if len(query) <= max_length:
        return query
    
    # 문장 단위로 자르기 시도
    sentences = query.split('.')
    truncated = ""
    
    for sentence in sentences:
        if len(truncated + sentence + ".") <= max_length - 50:  # 여유분 50자
            truncated += sentence + "."
        else:
            break
    
    # 문장 단위로 자르기가 안되면 단순 자르기
    if not truncated or len(truncated) < 100:
        truncated = query[:max_length-50] + "..."
    
    logger.warning(f"쿼리가 {len(query)}자에서 {len(truncated)}자로 축소됨")
    return truncated

def _format_references(references: list) -> str:
    """참조 문서를 링크로 포맷팅"""
    if not references:
        return ""
    
    formatted_refs = []
    for i, ref in enumerate(references[:5], 1):  # 최대 5개만
        title = ref.get('title', f'참고문서{i}')
        uri = ref.get('uri', '')
        relevance = ref.get('relevance_score', 0)
        
        # 파일명을 더 읽기 쉽게 변환
        display_name = title.replace('naver_blog_', '').replace('_', ' ').title()
        if not display_name or display_name == title:
            display_name = f"참고문서 {i}"
        
        # GCS URI를 API 프록시 링크로 변환
        if uri.startswith('gs://'):
            # gs://bucket/path -> /gcs/bucket/path
            bucket_and_path = uri[5:]  # 'gs://' 제거
            proxy_link = f"/gcs/{bucket_and_path}"
            formatted_refs.append(f"📄 [{display_name}]({proxy_link}) *(관련도: {relevance:.1f})*")
        else:
            formatted_refs.append(f"📄 {display_name}")
    
    return "\n\n---\n**📚 참고 문서:**\n" + "\n".join(formatted_refs)

def search_discovery_engine(query: str, max_results: int = 20) -> Dict[str, Any]:
    """Discovery Engine 검색 API 호출 - 문서 발견용 (샘플 코드 기반 개선)"""
    try:
        # ClientOptions으로 최적화된 클라이언트 생성
        from google.api_core.client_options import ClientOptions
        from google.cloud.discoveryengine_v1 import SearchServiceClient
        
        client_options = (
            ClientOptions(api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com")
            if LOCATION != "global"
            else None
        )
        search_client = SearchServiceClient(client_options=client_options)
        
        # 쿼리 길이 제한 적용
        truncated_query = _truncate_query(query)
        
        # Search Serving Config 경로 (샘플 코드와 일치)
        serving_config = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/engines/{ENGINE_ID}/servingConfigs/default_config"
        
        # 개선된 검색 요청 객체 생성 (summary_spec 추가)
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=truncated_query,
            page_size=max_results,
            content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True,
                    max_snippet_count=3
                ),
                # 검색 요약 기능 추가
                summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                    summary_result_count=5,
                    include_citations=True,
                    ignore_adversarial_query=True,
                    ignore_non_summary_seeking_query=False,
                    model_prompt_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelPromptSpec(
                        preamble="한국어로 상세한 답변을 제공해주세요."
                    ),
                    model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                        version="stable"
                    )
                )
            ),
            # 맞춤법 교정만 사용 (query_expansion_spec는 multi-datastore에서 지원 안됨)
            spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            )
        )
        
        # 검색 API 호출
        response = search_client.search(request)
        
        # 검색 결과 처리
        search_results = []
        for result in response.results:
            doc = result.document
            doc_data = {
                "id": doc.id,
                "title": doc.derived_struct_data.get("title", "제목없음"),
                "link": doc.derived_struct_data.get("link", ""),
                "snippets": []
            }
            
            # 스니펫 추출
            if "snippets" in doc.derived_struct_data:
                for snippet_info in doc.derived_struct_data["snippets"]:
                    if snippet_info.get("snippet_status") == "SUCCESS":
                        # HTML 태그 제거
                        snippet_text = snippet_info.get("snippet", "").replace("<b>", "").replace("</b>", "")
                        doc_data["snippets"].append(snippet_text)
            
            search_results.append(doc_data)
        
        # 검색 요약 정보 추출
        search_summary = None
        if hasattr(response, 'summary') and response.summary:
            search_summary = {
                "summary_text": response.summary.summary_text if hasattr(response.summary, 'summary_text') else "",
                "safety_attributes": response.summary.safety_attributes if hasattr(response.summary, 'safety_attributes') else None,
                "summary_skipped_reasons": response.summary.summary_skipped_reasons if hasattr(response.summary, 'summary_skipped_reasons') else []
            }
        
        logger.info(f"검색 API 결과: {len(search_results)}개 문서 발견, 요약: {'있음' if search_summary else '없음'}")
        
        return {
            "results": search_results,
            "total_size": response.total_size if hasattr(response, 'total_size') else len(search_results),
            "query": truncated_query,
            "summary": search_summary
        }
        
    except Exception as e:
        logger.error(f"Discovery Engine 검색 API 호출 오류: {str(e)}")
        return {
            "results": [],
            "total_size": 0,
            "query": query,
            "error": str(e)
        }

def _build_context_from_search_results(search_results: list, search_summary: dict = None, max_context_length: int = 1500) -> str:
    """검색 결과를 Answer API 컨텍스트로 변환 (요약 포함)"""
    if not search_results and not search_summary:
        return ""
    
    context_parts = []
    current_length = 0
    
    # 검색 요약이 있으면 우선 포함
    if search_summary and search_summary.get("summary_text"):
        summary_context = f"[검색 요약]\n{search_summary['summary_text']}\n\n"
        if len(summary_context) <= max_context_length // 3:  # 컨텍스트의 1/3까지만 요약에 할당
            context_parts.append(summary_context)
            current_length += len(summary_context)
    
    # 검색 결과 문서들 추가
    for i, result in enumerate(search_results[:8], 1):  # 요약이 있으면 문서 수 조금 줄임
        title = result.get("title", f"문서{i}")
        snippets = result.get("snippets", [])
        
        if not snippets:
            continue
            
        # 문서별 컨텍스트 구성
        doc_context = f"[문서{i}: {title}]\n"
        
        for snippet in snippets[:2]:  # 문서당 최대 2개 스니펫
            if current_length + len(doc_context) + len(snippet) > max_context_length:
                break
                
            doc_context += f"- {snippet.strip()}\n"
        
        if current_length + len(doc_context) <= max_context_length:
            context_parts.append(doc_context)
            current_length += len(doc_context)
        else:
            break
    
    context = "\n".join(context_parts)
    logger.info(f"검색 결과 컨텍스트 생성: {len(context)}자, {len(context_parts)}개 섹션 (요약 포함: {'예' if search_summary else '아니오'})")
    
    return context

def call_discovery_engine_with_search_context(query: str) -> Dict[str, Any]:
    """하이브리드 접근: 검색 API + Answer API"""
    try:
        # 1단계: 검색 API로 관련 문서 발견
        search_results = search_discovery_engine(query, max_results=15)
        
        if not search_results.get("results"):
            logger.warning("검색 결과가 없어 기존 Answer API 사용")
            return call_discovery_engine(query)
        
        # 2단계: 검색 결과를 컨텍스트로 변환 (요약 포함)
        search_context = _build_context_from_search_results(
            search_results["results"], 
            search_results.get("summary")
        )
        
        if not search_context:
            logger.warning("검색 컨텍스트 생성 실패, 기존 Answer API 사용")
            return call_discovery_engine(query)
        
        # 3단계: 검색 컨텍스트를 포함한 강화된 쿼리 생성
        enhanced_query = f"""질문: {query}

관련 참고 정보:
{search_context}

위 참고 정보를 바탕으로 질문에 대해 정확하고 상세한 답변을 해주세요."""
        
        # 4단계: Answer API 호출
        logger.info(f"하이브리드 쿼리 길이: {len(enhanced_query)}자")
        result = call_discovery_engine(enhanced_query)
        
        # 검색 결과 메타데이터 추가
        result["search_metadata"] = {
            "search_docs_found": len(search_results["results"]),
            "context_used": len(search_context),
            "hybrid_approach": True
        }
        
        return result
        
    except Exception as e:
        logger.error(f"하이브리드 접근 오류: {str(e)}, 기존 방식으로 대체")
        return call_discovery_engine(query)

async def call_discovery_engine_with_search_context_async(query: str) -> Dict[str, Any]:
    """하이브리드 접근 비동기 버전"""
    # 캐시 먼저 확인
    cached_response = _get_cached_response(query)
    if cached_response:
        logger.info(f"캐시된 응답 사용 (하이브리드 비동기): {query[:50]}...")
        return cached_response
    
    # 하이브리드 접근 사용
    return call_discovery_engine_with_search_context(query)

async def call_discovery_engine_async(query: str) -> Dict[str, Any]:
    """Discovery Engine API 비동기 호출"""
    # 캐시 먼저 확인
    cached_response = _get_cached_response(query)
    if cached_response:
        logger.info(f"캐시된 응답 사용 (비동기): {query[:50]}...")
        return cached_response
    
    # 캐시가 없으면 동기 함수 호출
    return call_discovery_engine(query)

def call_discovery_engine(query: str) -> Dict[str, Any]:
    """Discovery Engine API 호출 (샘플 코드 기반 개선)"""
    try:
        # 캐시 확인
        cached_response = _get_cached_response(query)
        if cached_response:
            logger.info(f"캐시된 응답 사용: {query[:50]}...")
            return cached_response
        
        # ClientOptions으로 최적화된 클라이언트 생성
        from google.api_core.client_options import ClientOptions
        
        client_options = (
            ClientOptions(api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com")
            if LOCATION != "global"
            else None
        )
        client = discoveryengine.ConversationalSearchServiceClient(client_options=client_options)
        
        # 쿼리 길이 제한 적용
        truncated_query = _truncate_query(query)
        
        # Search Serving Config 리소스 경로 구성
        serving_config = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/engines/{ENGINE_ID}/servingConfigs/default_serving_config"
        
        # Query Understanding 설정 (샘플 코드 기반 개선)
        query_understanding_spec = discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec(
            query_rephraser_spec=discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec.QueryRephraserSpec(
                disable=False,
                max_rephrase_steps=1,
            ),
            query_classification_spec=discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec.QueryClassificationSpec(
                types=[
                    discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec.QueryClassificationSpec.Type.ADVERSARIAL_QUERY,
                    discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec.QueryClassificationSpec.Type.NON_ANSWER_SEEKING_QUERY,
                ]
            ),
        )
        
        # Answer Generation 설정 (샘플 코드 기반 개선)
        answer_generation_spec = discoveryengine.AnswerQueryRequest.AnswerGenerationSpec(
            ignore_adversarial_query=False,
            ignore_non_answer_seeking_query=False,
            ignore_low_relevant_content=False,
            # 최신 모델 사용
            model_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.ModelSpec(
                model_version="gemini-2.0-flash-001/answer_gen/v1"
            ),
            prompt_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.PromptSpec(
                preamble="한국어로 정확하고 상세한 답변을 제공해주세요. 가격이나 비용 정보가 있다면 구체적으로 포함해주세요.",
            ),
            include_citations=True,
            answer_language_code="ko",
        )
        
        # 요청 객체 생성
        request = discoveryengine.AnswerQueryRequest(
            serving_config=serving_config,
            query=discoveryengine.Query(text=truncated_query),
            session=None,
            query_understanding_spec=query_understanding_spec,
            answer_generation_spec=answer_generation_spec,
        )
        
        # API 호출
        response = client.answer_query(request)
        
        # 참조 정보 추출
        references = []
        if response.answer and hasattr(response.answer, 'references') and response.answer.references:
            references = [
                {
                    "content": ref.chunk_info.content if ref.chunk_info else "",
                    "relevance_score": ref.chunk_info.relevance_score if ref.chunk_info else 0.0,
                    "title": ref.chunk_info.document_metadata.title if ref.chunk_info and ref.chunk_info.document_metadata else "",
                    "uri": ref.chunk_info.document_metadata.uri if ref.chunk_info and ref.chunk_info.document_metadata else ""
                }
                for ref in response.answer.references
            ]
        
        # 답변 텍스트에 참조 링크 추가
        answer_text = response.answer.answer_text if response.answer else ""
        reference_links = _format_references(references)
        enhanced_answer = answer_text + reference_links
        
        # 응답 변환
        result = {
            "answer_text": enhanced_answer,
            "citations": [
                {
                    "start_index": c.start_index,
                    "end_index": c.end_index,
                    "reference_ids": [s.reference_id for s in c.sources] if c.sources else []
                }
                for c in response.answer.citations
            ] if response.answer and response.answer.citations else [],
            "references": references
        }
        
        # 캐시에 저장
        _cache_response(query, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Discovery Engine API 호출 오류: {str(e)}")
        raise DiscoveryEngineAPIError(f"Discovery Engine API 호출 실패: {str(e)}", str(e))

async def generate_triple_based_answer_async(user_prompt: str, triples: list) -> Dict[str, Any]:
    """Triple 정보를 기반으로 Discovery Engine을 통해 답변 생성 (비동기) - 하이브리드 접근"""
    if not triples:
        return await call_discovery_engine_with_search_context_async(user_prompt)
    
    # Triple 정보를 적절히 제한해서 포함
    max_triple_length = 800  # Triple 정보 최대 길이 (검색 컨텍스트 공간 확보)
    triple_text = "\n".join(triples)
    
    if len(triple_text) > max_triple_length:
        triple_text = triple_text[:max_triple_length] + "..."
        logger.warning(f"Triple 텍스트가 {len(triple_text)}자로 축소됨")
    
    # 하이브리드 접근: 검색으로 추가 컨텍스트 수집
    search_results = search_discovery_engine(user_prompt, max_results=10)
    search_context = _build_context_from_search_results(
        search_results.get("results", []), 
        search_results.get("summary"),
        max_context_length=700  # Triple과 균형 맞춤
    )
    
    # 강화된 쿼리 생성
    enhanced_query = f"""질문: {user_prompt}

데이터베이스 Triple 정보:
{triple_text}

검색된 추가 참고 정보:
{search_context}

위 모든 정보를 종합하여 정확하고 상세한 답변을 해주세요."""
    
    result = await call_discovery_engine_async(enhanced_query)
    
    # 메타데이터 추가
    result["hybrid_metadata"] = {
        "triple_count": len(triples),
        "search_docs_found": len(search_results.get("results", [])),
        "combined_approach": True
    }
    
    return result

def generate_triple_based_answer(user_prompt: str, triples: list) -> Dict[str, Any]:
    """Triple 정보를 기반으로 Discovery Engine을 통해 답변 생성 - 하이브리드 접근"""
    if not triples:
        return call_discovery_engine_with_search_context(user_prompt)
    
    # Triple 정보를 적절히 제한해서 포함
    max_triple_length = 800  # Triple 정보 최대 길이 (검색 컨텍스트 공간 확보)
    triple_text = "\n".join(triples)
    
    if len(triple_text) > max_triple_length:
        triple_text = triple_text[:max_triple_length] + "..."
        logger.warning(f"Triple 텍스트가 {len(triple_text)}자로 축소됨")
    
    # 하이브리드 접근: 검색으로 추가 컨텍스트 수집
    search_results = search_discovery_engine(user_prompt, max_results=10)
    search_context = _build_context_from_search_results(
        search_results.get("results", []), 
        search_results.get("summary"),
        max_context_length=700  # Triple과 균형 맞춤
    )
    
    # 강화된 쿼리 생성
    enhanced_query = f"""질문: {user_prompt}

데이터베이스 Triple 정보:
{triple_text}

검색된 추가 참고 정보:
{search_context}

위 모든 정보를 종합하여 정확하고 상세한 답변을 해주세요."""
    
    result = call_discovery_engine(enhanced_query)
    
    # 메타데이터 추가
    result["hybrid_metadata"] = {
        "triple_count": len(triples),
        "search_docs_found": len(search_results.get("results", [])),
        "combined_approach": True
    }
    
    return result

def generate_summary_answer(triple_answer: str, discovery_answer: str, user_prompt: str) -> Dict[str, Any]:
    """Triple 답변과 Discovery Engine 답변을 결합하여 최종 답변 생성"""
    # 답변들을 적절히 요약해서 쿼리 길이 제한 내에서 처리
    max_answer_length = 1500  # 각 답변당 최대 길이
    
    truncated_triple = triple_answer[:max_answer_length] + "..." if len(triple_answer) > max_answer_length else triple_answer
    truncated_discovery = discovery_answer[:max_answer_length] + "..." if len(discovery_answer) > max_answer_length else discovery_answer
    
    combined_query = f"""질문: {user_prompt}

참고답변1: {truncated_triple}

참고답변2: {truncated_discovery}

위 정보를 종합하여 답변해주세요."""
    
    return call_discovery_engine(combined_query)