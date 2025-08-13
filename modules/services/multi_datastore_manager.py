"""다중 데이터스토어 관리 모듈"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from google.cloud import discoveryengine_v1
from google.api_core import exceptions

from ..config import Config
from ..auth import get_credentials

logger = logging.getLogger(__name__)

class MultiDatastoreManager:
    """다중 데이터스토어 관리 클래스"""
    
    def __init__(self):
        self.credentials = get_credentials()
        self.project_id = Config.PROJECT_ID
        self.discovery_location = Config.DISCOVERY_LOCATION
        self.serving_config = Config.DISCOVERY_SERVING_CONFIG
        self.datastores_config = Config.get_datastores_config()
        
        # Discovery Engine 클라이언트
        self.search_client = discoveryengine_v1.SearchServiceClient(
            credentials=self.credentials
        )
        
        # 스레드 풀 (동시 검색용)
        self.executor = ThreadPoolExecutor(max_workers=5)
        
    def get_enabled_datastores(self) -> Dict[str, Dict[str, str]]:
        """활성화된 데이터스토어 목록 반환"""
        return {
            name: config 
            for name, config in self.datastores_config.items()
            if config.get('enabled', True)
        }
    
    def get_datastore_serving_config(self, datastore_name: str) -> str:
        """데이터스토어별 serving config 경로 생성"""
        try:
            datastore_path = Config.get_datastore_path(datastore_name)
            return f"{datastore_path}/servingConfigs/{self.serving_config}"
        except ValueError as e:
            logger.error(f"데이터스토어 경로 생성 실패: {e}")
            raise
    
    async def search_single_datastore(
        self, 
        datastore_name: str, 
        query: str,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """단일 데이터스토어에서 검색"""
        try:
            serving_config = self.get_datastore_serving_config(datastore_name)
            
            # 검색 요청 구성
            request = discoveryengine_v1.SearchRequest(
                serving_config=serving_config,
                query=query,
                page_size=max_results,
                query_expansion_spec=discoveryengine_v1.SearchRequest.QueryExpansionSpec(
                    condition=discoveryengine_v1.SearchRequest.QueryExpansionSpec.Condition.AUTO
                ),
                spell_correction_spec=discoveryengine_v1.SearchRequest.SpellCorrectionSpec(
                    mode=discoveryengine_v1.SearchRequest.SpellCorrectionSpec.Mode.AUTO
                )
            )
            
            # 비동기 검색 실행
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor, 
                self.search_client.search, 
                request
            )
            
            # 결과 파싱
            results = []
            for result in response.results:
                document = result.document
                results.append({
                    'id': document.id,
                    'title': document.derived_struct_data.get('title', ''),
                    'content': document.derived_struct_data.get('content', ''),
                    'uri': document.derived_struct_data.get('uri', ''),
                    'relevance_score': getattr(result, 'relevance_score', 0.0),
                    'datastore': datastore_name
                })
            
            return {
                'datastore': datastore_name,
                'results': results,
                'success': True,
                'total_size': response.total_size
            }
            
        except exceptions.NotFound:
            logger.warning(f"데이터스토어 '{datastore_name}'를 찾을 수 없습니다")
            return {
                'datastore': datastore_name,
                'results': [],
                'success': False,
                'error': 'Datastore not found'
            }
        except Exception as e:
            logger.error(f"데이터스토어 '{datastore_name}' 검색 실패: {e}")
            return {
                'datastore': datastore_name,
                'results': [],
                'success': False,
                'error': str(e)
            }
    
    async def search_multiple_datastores(
        self,
        query: str,
        datastores: Optional[List[str]] = None,
        max_results_per_datastore: int = 3,
        aggregate_results: bool = True
    ) -> Dict[str, Any]:
        """다중 데이터스토어에서 동시 검색"""
        
        # 검색할 데이터스토어 결정
        if datastores is None:
            enabled_datastores = self.get_enabled_datastores()
            datastores = list(enabled_datastores.keys())
        
        logger.info(f"다중 데이터스토어 검색 시작: {datastores}")
        
        # 동시 검색 실행
        search_tasks = [
            self.search_single_datastore(ds_name, query, max_results_per_datastore)
            for ds_name in datastores
        ]
        
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # 결과 정리
        successful_results = []
        failed_datastores = []
        
        for i, result in enumerate(search_results):
            if isinstance(result, Exception):
                logger.error(f"데이터스토어 '{datastores[i]}' 검색 중 예외: {result}")
                failed_datastores.append({
                    'datastore': datastores[i],
                    'error': str(result)
                })
            elif result['success']:
                successful_results.append(result)
            else:
                failed_datastores.append(result)
        
        # 결과 집계
        if aggregate_results:
            aggregated_results = self._aggregate_search_results(successful_results)
        else:
            aggregated_results = successful_results
        
        return {
            'query': query,
            'successful_datastores': len(successful_results),
            'failed_datastores': len(failed_datastores),
            'results': aggregated_results,
            'failures': failed_datastores,
            'total_results': sum(len(r['results']) for r in successful_results)
        }
    
    def _aggregate_search_results(self, datastore_results: List[Dict]) -> List[Dict]:
        """검색 결과를 관련성 점수 기준으로 집계"""
        all_results = []
        
        for ds_result in datastore_results:
            all_results.extend(ds_result['results'])
        
        # 관련성 점수 기준 정렬
        all_results.sort(key=lambda x: x.get('relevance_score', 0.0), reverse=True)
        
        return all_results
    
    async def get_answer_from_multiple_datastores(
        self,
        query: str,
        datastores: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """다중 데이터스토어에서 답변 생성"""
        
        # 다중 검색 실행
        search_result = await self.search_multiple_datastores(
            query=query,
            datastores=datastores,
            max_results_per_datastore=5
        )
        
        if search_result['total_results'] == 0:
            return {
                'answer_text': '죄송하지만 관련 정보를 찾을 수 없습니다.',
                'search_results': [],
                'citations': [],
                'successful_datastores': search_result['successful_datastores'],
                'failed_datastores': search_result['failed_datastores'],
                'query_id': f"multi_search_{hash(query)}",
                'session_id': session_id
            }
        
        # 최상위 결과들로 답변 구성
        top_results = search_result['results'][:10]
        
        # 답변 텍스트 생성 (간단한 추출 기반)
        answer_text = self._generate_answer_from_results(top_results, query)
        
        # 인용 정보 생성
        citations = self._generate_citations(top_results)
        
        return {
            'answer_text': answer_text,
            'search_results': top_results,
            'citations': citations,
            'successful_datastores': search_result['successful_datastores'],
            'failed_datastores': search_result['failed_datastores'],
            'total_results': search_result['total_results'],
            'query_id': f"multi_search_{hash(query)}",
            'session_id': session_id
        }
    
    def _generate_answer_from_results(self, results: List[Dict], query: str) -> str:
        """검색 결과에서 답변 생성"""
        if not results:
            return "관련 정보를 찾을 수 없습니다."
        
        # 가장 관련성 높은 결과들의 내용 조합
        answer_parts = []
        used_datastores = set()
        
        for result in results[:3]:  # 상위 3개 결과 사용
            content = result.get('content', '').strip()
            datastore = result.get('datastore', 'unknown')
            
            if content and len(content) > 50:
                answer_parts.append(content[:500])  # 최대 500자
                used_datastores.add(datastore)
        
        if answer_parts:
            answer = " ".join(answer_parts)
            
            # 데이터스토어 출처 정보 추가
            if len(used_datastores) > 1:
                answer += f"\n\n(참조: {', '.join(used_datastores)} 데이터스토어)"
            
            return answer
        else:
            return "검색된 결과에서 충분한 정보를 추출할 수 없습니다."
    
    def _generate_citations(self, results: List[Dict]) -> List[Dict]:
        """검색 결과에서 인용 정보 생성"""
        citations = []
        
        for i, result in enumerate(results[:5]):  # 상위 5개만 인용
            if result.get('title') and result.get('uri'):
                citations.append({
                    'title': result['title'],
                    'uri': result['uri'],
                    'snippet': result.get('content', '')[:200],
                    'datastore': result.get('datastore', 'unknown'),
                    'relevance_score': result.get('relevance_score', 0.0)
                })
        
        return citations
    
    def add_datastore_config(self, name: str, config: Dict[str, Any]) -> bool:
        """런타임에 새 데이터스토어 설정 추가"""
        try:
            # 기본값 설정
            datastore_config = {
                'id': config.get('id', f"{self.project_id}-{name}-datastore"),
                'location': config.get('location', 'global'),
                'type': config.get('type', 'unstructured'),
                'enabled': config.get('enabled', True)
            }
            
            # 설정 추가
            self.datastores_config[name] = datastore_config
            
            logger.info(f"데이터스토어 설정 추가됨: {name}")
            return True
            
        except Exception as e:
            logger.error(f"데이터스토어 설정 추가 실패: {e}")
            return False
    
    def remove_datastore_config(self, name: str) -> bool:
        """데이터스토어 설정 제거"""
        if name == 'default':
            logger.warning("기본 데이터스토어는 제거할 수 없습니다")
            return False
        
        if name in self.datastores_config:
            del self.datastores_config[name]
            logger.info(f"데이터스토어 설정 제거됨: {name}")
            return True
        else:
            logger.warning(f"존재하지 않는 데이터스토어: {name}")
            return False
    
    def __del__(self):
        """리소스 정리"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

# 글로벌 인스턴스
multi_datastore_manager = MultiDatastoreManager()