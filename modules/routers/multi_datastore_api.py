"""다중 데이터스토어 API 라우터"""
import json
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Form, Query
from fastapi.responses import JSONResponse

from ..auth import is_authenticated
from ..services.multi_datastore_manager import multi_datastore_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/datastores')
async def list_datastores():
    """활성화된 데이터스토어 목록 조회"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="서버 인증 실패")
    
    try:
        datastores = multi_datastore_manager.get_enabled_datastores()
        return JSONResponse({
            "success": True,
            "datastores": datastores,
            "count": len(datastores)
        })
    except Exception as e:
        logger.error(f"데이터스토어 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"데이터스토어 목록 조회 실패: {str(e)}")

@router.post('/api/datastores/search')
async def search_multiple_datastores(
    userPrompt: str = Form(...),
    datastores: str = Form("[]"),  # JSON 배열 문자열
    maxResults: int = Form(5),
    aggregateResults: bool = Form(True)
):
    """다중 데이터스토어에서 검색"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="서버 인증 실패")
    
    try:
        # 데이터스토어 목록 파싱
        try:
            datastore_list = json.loads(datastores) if datastores != "[]" else None
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="잘못된 데이터스토어 목록 형식")
        
        # 검색 실행
        result = await multi_datastore_manager.search_multiple_datastores(
            query=userPrompt,
            datastores=datastore_list,
            max_results_per_datastore=maxResults,
            aggregate_results=aggregateResults
        )
        
        return JSONResponse({
            "success": True,
            "query": result['query'],
            "successful_datastores": result['successful_datastores'],
            "failed_datastores": result['failed_datastores'],
            "total_results": result['total_results'],
            "results": result['results'],
            "failures": result['failures']
        })
        
    except Exception as e:
        logger.error(f"다중 데이터스토어 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")

@router.post('/api/datastores/answer')
async def get_answer_from_multiple_datastores(
    userPrompt: str = Form(...),
    datastores: str = Form("[]"),
    sessionId: str = Form("")
):
    """다중 데이터스토어에서 답변 생성"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="서버 인증 실패")
    
    try:
        # 데이터스토어 목록 파싱
        try:
            datastore_list = json.loads(datastores) if datastores != "[]" else None
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="잘못된 데이터스토어 목록 형식")
        
        # 답변 생성
        result = await multi_datastore_manager.get_answer_from_multiple_datastores(
            query=userPrompt,
            datastores=datastore_list,
            session_id=sessionId or None
        )
        
        return JSONResponse({
            "success": True,
            "answer": result['answer_text'],
            "search_results": result['search_results'],
            "citations": result['citations'],
            "successful_datastores": result['successful_datastores'],
            "failed_datastores": result['failed_datastores'],
            "total_results": result.get('total_results', 0),
            "query_id": result['query_id'],
            "session_id": result['session_id'],
            "metadata": {
                "engine_type": "multi_datastore",
                "datastores_used": len(result.get('search_results', []))
            }
        })
        
    except Exception as e:
        logger.error(f"다중 데이터스토어 답변 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"답변 생성 실패: {str(e)}")

@router.post('/api/datastores/add')
async def add_datastore_config(
    name: str = Form(...),
    datastore_id: str = Form(""),
    location: str = Form("global"),
    datastore_type: str = Form("unstructured"),
    enabled: bool = Form(True)
):
    """새 데이터스토어 설정 추가"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="서버 인증 실패")
    
    try:
        # 입력 검증
        if not name or name == 'default':
            raise HTTPException(status_code=400, detail="유효하지 않은 데이터스토어 이름")
        
        config = {
            'id': datastore_id or f"{multi_datastore_manager.project_id}-{name}-datastore",
            'location': location,
            'type': datastore_type,
            'enabled': enabled
        }
        
        # 설정 추가
        success = multi_datastore_manager.add_datastore_config(name, config)
        
        if success:
            return JSONResponse({
                "success": True,
                "message": f"데이터스토어 '{name}' 설정이 추가되었습니다",
                "config": config
            })
        else:
            raise HTTPException(status_code=500, detail="데이터스토어 설정 추가 실패")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"데이터스토어 설정 추가 실패: {e}")
        raise HTTPException(status_code=500, detail=f"설정 추가 실패: {str(e)}")

@router.delete('/api/datastores/{datastore_name}')
async def remove_datastore_config(datastore_name: str):
    """데이터스토어 설정 제거"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="서버 인증 실패")
    
    try:
        if datastore_name == 'default':
            raise HTTPException(status_code=400, detail="기본 데이터스토어는 제거할 수 없습니다")
        
        success = multi_datastore_manager.remove_datastore_config(datastore_name)
        
        if success:
            return JSONResponse({
                "success": True,
                "message": f"데이터스토어 '{datastore_name}' 설정이 제거되었습니다"
            })
        else:
            raise HTTPException(status_code=404, detail="존재하지 않는 데이터스토어")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"데이터스토어 설정 제거 실패: {e}")
        raise HTTPException(status_code=500, detail=f"설정 제거 실패: {str(e)}")

@router.get('/api/datastores/{datastore_name}/test')
async def test_datastore_connection(datastore_name: str):
    """특정 데이터스토어 연결 테스트"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="서버 인증 실패")
    
    try:
        # 테스트 검색 수행
        result = await multi_datastore_manager.search_single_datastore(
            datastore_name=datastore_name,
            query="test connection",
            max_results=1
        )
        
        if result['success']:
            return JSONResponse({
                "success": True,
                "message": f"데이터스토어 '{datastore_name}' 연결 성공",
                "datastore": datastore_name,
                "test_results": len(result['results'])
            })
        else:
            return JSONResponse({
                "success": False,
                "message": f"데이터스토어 '{datastore_name}' 연결 실패",
                "error": result.get('error', 'Unknown error')
            }, status_code=400)
            
    except Exception as e:
        logger.error(f"데이터스토어 연결 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"연결 테스트 실패: {str(e)}")

@router.get('/api/datastores/config/example')
async def get_datastore_config_example():
    """데이터스토어 설정 예시 반환"""
    return JSONResponse({
        "success": True,
        "example_env_config": {
            "DATASTORES_CONFIG": {
                "docs": {
                    "id": "project-docs-datastore",
                    "location": "global",
                    "type": "unstructured",
                    "enabled": True
                },
                "faq": {
                    "id": "project-faq-datastore", 
                    "location": "asia-northeast3",
                    "type": "structured",
                    "enabled": True
                },
                "archives": {
                    "id": "project-archives-datastore",
                    "location": "global",
                    "type": "unstructured",
                    "enabled": False
                }
            }
        },
        "setup_command_example": 'ADDITIONAL_DATASTORES=\'{"docs":{"type":"unstructured"},"faq":{"type":"structured"}}\' python setup.py',
        "description": "환경변수 DATASTORES_CONFIG 또는 setup.py 실행 시 ADDITIONAL_DATASTORES로 다중 데이터스토어 설정 가능"
    })