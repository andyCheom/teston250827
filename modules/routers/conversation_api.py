"""대화 로그 관리 API 엔드포인트"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ..services.conversation_logger import conversation_logger

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/conversations/sessions')
async def list_conversation_sessions(
    limit: int = Query(50, ge=1, le=100, description="최대 조회 개수")
) -> JSONResponse:
    """모든 대화 세션 목록 조회"""
    try:
        sessions = conversation_logger.list_sessions()
        
        # limit 적용
        if limit < len(sessions):
            sessions = sessions[:limit]
        
        return JSONResponse({
            "sessions": sessions,
            "total_count": len(sessions),
            "limit": limit
        })
        
    except Exception as e:
        logger.error(f"세션 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="세션 목록 조회 실패")

@router.get('/api/conversations/sessions/{session_id}')
async def get_session_conversations(session_id: str) -> JSONResponse:
    """특정 세션의 대화 내용 조회"""
    try:
        # 세션 정보 조회
        session_info = conversation_logger.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        # 대화 내용 조회
        conversations = conversation_logger.get_session_conversations(session_id)
        if conversations is None:
            raise HTTPException(status_code=404, detail="대화 내용을 찾을 수 없습니다")
        
        return JSONResponse({
            "session_info": session_info,
            "conversations": conversations
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 대화 조회 실패 {session_id}: {e}")
        raise HTTPException(status_code=500, detail="세션 대화 조회 실패")

@router.get('/api/conversations/sessions/{session_id}/info')
async def get_session_info(session_id: str) -> JSONResponse:
    """특정 세션의 정보만 조회 (대화 내용 제외)"""
    try:
        session_info = conversation_logger.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        return JSONResponse(session_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 정보 조회 실패 {session_id}: {e}")
        raise HTTPException(status_code=500, detail="세션 정보 조회 실패")

@router.delete('/api/conversations/cleanup')
async def cleanup_old_sessions(
    days: int = Query(30, ge=1, le=365, description="보관할 일수")
) -> JSONResponse:
    """오래된 대화 세션 파일들 정리"""
    try:
        deleted_count = conversation_logger.cleanup_old_sessions(days_to_keep=days)
        
        return JSONResponse({
            "message": f"{days}일 이전의 세션 파일들을 정리했습니다",
            "deleted_count": deleted_count
        })
        
    except Exception as e:
        logger.error(f"세션 정리 실패: {e}")
        raise HTTPException(status_code=500, detail="세션 정리 실패")

@router.get('/api/conversations/stats')
async def get_conversation_stats() -> JSONResponse:
    """대화 로그 통계 정보"""
    try:
        sessions = conversation_logger.list_sessions()
        
        if not sessions:
            return JSONResponse({
                "total_sessions": 0,
                "total_conversations": 0,
                "latest_session": None,
                "oldest_session": None
            })
        
        # 통계 계산
        total_sessions = len(sessions)
        total_conversations = sum(session["conversation_count"] for session in sessions)
        latest_session = sessions[0]  # 이미 최신순 정렬됨
        oldest_session = sessions[-1]
        
        return JSONResponse({
            "total_sessions": total_sessions,
            "total_conversations": total_conversations,
            "latest_session": {
                "session_id": latest_session["session_id"],
                "updated_at": latest_session["updated_at"],
                "conversation_count": latest_session["conversation_count"]
            },
            "oldest_session": {
                "session_id": oldest_session["session_id"],
                "created_at": oldest_session["created_at"],
                "conversation_count": oldest_session["conversation_count"]
            }
        })
        
    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="통계 조회 실패")