"""데이터베이스 연결 및 쿼리 모듈"""
import json
import logging
from functools import lru_cache
from typing import List
from google.cloud import spanner

from .config import Config
from .cache import memory_cache, get_cache_key
from .auth import get_spanner_client

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_database_connection():
    """Spanner 데이터베이스 연결을 캐시하여 재사용"""
    spanner_client = get_spanner_client()
    if spanner_client is None:
        raise RuntimeError("Spanner client가 초기화되지 않았습니다.")
    
    instance = spanner_client.instance(Config._get_required_env('SPANNER_INSTANCE_ID'))
    return instance.database(Config._get_required_env('SPANNER_DATABASE_ID'))

def query_spanner_triples(user_prompt: str) -> List[str]:
    """사용자 프롬프트로 Spanner에서 Triple 검색"""
    # 캐시 확인
    cache_key = get_cache_key("spanner_triples", user_prompt)
    cached_result = memory_cache.get(cache_key)
    if cached_result is not None:
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
        table_name = Config._get_required_env('SPANNER_TABLE_NAME')
        query = f"""
        SELECT subject, predicate, object FROM `{table_name}`
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
    """Triple 요소로 Spanner 검색"""
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
        table_name = Config._get_required_env('SPANNER_TABLE_NAME')
        query = f"""
        SELECT subject, predicate, object FROM `{table_name}`
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