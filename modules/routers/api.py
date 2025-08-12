"""FastAPI 라우터 모듈"""
import json
import logging
import os
import mimetypes
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import JSONResponse, StreamingResponse

from ..config import Config
from ..auth import is_authenticated, get_storage_client
from ..services.discovery_engine_api import get_complete_discovery_answer
from ..services.conversation_logger import conversation_logger
from ..services.sensitive_query_detector import sensitive_detector
from ..services.consultant_service import consultant_service
from ..services.demo_request_service import demo_service
from ..services.firestore_conversation import firestore_conversation

logger = logging.getLogger(__name__)
router = APIRouter()

def get_short_session_id(long_session_id: str) -> str:
    """긴 Discovery Engine 세션 ID를 짧은 형태로 변환"""
    if not long_session_id:
        return f"session_{int(datetime.now().timestamp())}"
    
    # Discovery Engine 세션 ID에서 마지막 부분만 추출
    if "/" in long_session_id:
        session_part = long_session_id.split("/")[-1]
    else:
        session_part = long_session_id
    
    # 너무 길면 해시로 줄이기
    if len(session_part) > 50:
        import hashlib
        hash_part = hashlib.md5(session_part.encode()).hexdigest()[:16]
        return f"session_{hash_part}"
    
    return f"session_{session_part}"

@router.get('/api/health')
async def health_check():
    """기본 헬스 체크 엔드포인트 - 빠른 응답"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "graphrag-api",
        "version": "2.0.0"
    }

@router.get('/api/health/detailed')
async def detailed_health_check():
    """상세 헬스 체크 엔드포인트 - 인증 포함"""
    from main import get_auth_status
    try:
        # 백그라운드 인증 상태 확인 (빠른 응답)
        auth_status = get_auth_status()
        
        # 실제 인증 함수도 확인 (선택적)
        try:
            from ..auth import is_authenticated
            detailed_auth_status = is_authenticated()
        except:
            detailed_auth_status = auth_status
        
        return {
            "status": "healthy" if auth_status else "degraded",
            "authenticated": auth_status,
            "detailed_auth": detailed_auth_status,
            "timestamp": datetime.now().isoformat(),
            "service": "graphrag-api",
            "version": "2.0.0",
            "components": {
                "auth": "ok" if auth_status else "warning",
                "api": "ok",
                "detailed_auth": "ok" if detailed_auth_status else "warning"
            }
        }
    except Exception as e:
        logger.warning(f"인증 상태 확인 실패: {e}")
        return {
            "status": "degraded",
            "authenticated": False,
            "timestamp": datetime.now().isoformat(),
            "service": "graphrag-api",
            "version": "2.0.0",
            "components": {
                "auth": "error",
                "api": "ok"
            },
            "error": str(e)
        }

# _build_vertex_payload 함수는 더 이상 사용하지 않음 - Discovery Engine으로 대체됨

@router.post('/api/generate')
async def generate_content(userPrompt: str = Form(""), conversationHistory: str = Form("[]"), sessionId: str = Form("")):
    """메인 답변 생성 엔드포인트 - Discovery Engine 사용"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="서버 인증 실패 - Google Cloud 인증을 확인하세요")

    try:
        conversation_history = json.loads(conversationHistory)
        
        # 민감한 질문 감지 및 지능적 분류
        sensitivity_check = sensitive_detector.is_sensitive_query(userPrompt)
        
        # RAG 우선 시도가 필요한 경우 (요금제/플랜 일반 정보)
        if sensitivity_check["should_try_rag_first"]:
            logger.info(f"요금제/플랜 일반 정보 질문으로 분류, RAG 우선 시도: {userPrompt[:50]}...")
            
            try:
                # Discovery Engine을 통한 답변 시도
                discovery_result = await get_complete_discovery_answer(userPrompt)
                answer_text = discovery_result.get("answer_text", "")
                
                # RAG 답변이 충분한지 확인
                if answer_text and len(answer_text.strip()) > 50:
                    # RAG 답변 성공 - 일반적인 플로우로 처리
                    logger.info(f"RAG 답변 성공: {len(answer_text)}자")
                    # 아래 일반 처리 로직으로 넘어감
                    
                else:
                    # RAG 답변이 부족한 경우 상담사 연결 제안
                    logger.info("RAG 답변이 부족하여 상담사 연결로 전환")
                    fallback_response = f"{sensitive_detector.get_sensitive_response(['general_plan_info'])}"
                    
                    updated_history = conversation_history + [{
                        "role": "user", 
                        "parts": [{"text": userPrompt}]
                    }, {
                        "role": "model",
                        "parts": [{"text": fallback_response}]
                    }]
                    
                    return JSONResponse({
                        "answer": fallback_response,
                        "summary_answer": fallback_response,
                        "citations": discovery_result.get("citations", []),
                        "search_results": discovery_result.get("search_results", []),
                        "related_questions": discovery_result.get("related_questions", []),
                        "updatedHistory": updated_history,
                        "metadata": {
                            "engine_type": "rag_fallback_to_consultant",
                            "sensitive_detected": True,
                            "sensitive_categories": ["rag_insufficient"],
                            "confidence": sensitivity_check["confidence"],
                            "query_type": sensitivity_check["query_type"]
                        },
                        "quality_check": {
                            "has_answer": True,
                            "discovery_success": False,
                            "rag_attempted": True,
                            "rag_insufficient": True
                        },
                        "consultant_needed": True
                    })
                    
            except Exception as e:
                logger.error(f"RAG 시도 중 오류 발생, 상담사 연결로 전환: {e}")
                fallback_response = f"{sensitive_detector.get_sensitive_response(['general_plan_info'])}"
                
                updated_history = conversation_history + [{
                    "role": "user", 
                    "parts": [{"text": userPrompt}]
                }, {
                    "role": "model",
                    "parts": [{"text": fallback_response}]
                }]
                
                return JSONResponse({
                    "answer": fallback_response,
                    "summary_answer": fallback_response,
                    "citations": [],
                    "search_results": [],
                    "related_questions": [],
                    "updatedHistory": updated_history,
                    "metadata": {
                        "engine_type": "rag_error_to_consultant",
                        "sensitive_detected": True,
                        "sensitive_categories": ["rag_error"],
                        "confidence": sensitivity_check["confidence"],
                        "query_type": sensitivity_check["query_type"],
                        "error": str(e)
                    },
                    "quality_check": {
                        "has_answer": True,
                        "discovery_success": False,
                        "rag_attempted": True,
                        "rag_error": True
                    },
                    "consultant_needed": True
                })
        
        # 즉시 상담사 연결이 필요한 민감한 질문
        elif sensitivity_check["is_sensitive"]:
            # 민감한 질문에 대한 표준 응답
            sensitive_response = sensitive_detector.get_sensitive_response(sensitivity_check["categories"])
            
            # 대화 히스토리 업데이트
            updated_history = conversation_history + [{
                "role": "user", 
                "parts": [{"text": userPrompt}]
            }, {
                "role": "model",
                "parts": [{"text": sensitive_response}]
            }]
            
            logger.info(f"민감한 질문 감지됨: {userPrompt[:50]}... -> 카테고리: {sensitivity_check['categories']}")
            
            return JSONResponse({
                "answer": sensitive_response,
                "summary_answer": sensitive_response,
                "citations": [],
                "search_results": [],
                "related_questions": [],
                "updatedHistory": updated_history,
                "metadata": {
                    "engine_type": "sensitive_query_handler",
                    "sensitive_detected": True,
                    "sensitive_categories": sensitivity_check["categories"],
                    "confidence": sensitivity_check["confidence"],
                    "query_type": sensitivity_check["query_type"]
                },
                "quality_check": {
                    "has_answer": True,
                    "discovery_success": False,
                    "sensitive_query": True
                },
                "consultant_needed": True  # 프론트엔드에서 상담사 연결 버튼 표시용
            })
        
        # Discovery Engine을 통한 답변 생성
        discovery_result = await get_complete_discovery_answer(userPrompt)
        
        # 답변 텍스트 추출
        answer_text = discovery_result.get("answer_text", "")
        
        # 디버그 로깅
        logger.info(f"Discovery 결과 - answer_text: {len(answer_text)}자")
        if not answer_text:
            logger.warning("빈 answer_text 감지!")
            logger.debug(f"Discovery result keys: {list(discovery_result.keys())}")
        
        # 최종 답변 생성
        if answer_text and answer_text.strip():
            final_answer = answer_text
        else:
            # 기본 답변 - Discovery Engine에서 아무것도 찾지 못한 경우
            final_answer = "죄송하지만 관련 정보를 찾을 수 없습니다. 처음서비스와 관련된 구체적인 질문을 해주시면 더 정확한 답변을 제공할 수 있습니다."
            logger.warning(f"기본 답변 사용 - 원래 answer_text: '{answer_text}'")
        
        # 대화 히스토리 업데이트
        updated_history = conversation_history + [{
            "role": "user", 
            "parts": [{"text": userPrompt}]
        }, {
            "role": "model",
            "parts": [{"text": final_answer}]
        }]
        
        logger.info(json.dumps({
            "stage": "discovery_main_answer_generated",
            "user_prompt": userPrompt,
            "answer_length": len(final_answer),
            "citations_count": len(discovery_result.get("citations", [])),
            "search_results_count": len(discovery_result.get("search_results", []))
        }, ensure_ascii=False))

        # 대화 내용 JSON 파일에 로깅
        session_id = discovery_result.get("session_id")
        conversation_metadata = {
            "citations": discovery_result.get("citations", []),
            "search_results": discovery_result.get("search_results", []),
            "related_questions": discovery_result.get("related_questions", []),
            "engine_type": "discovery_engine_main",
            "query_id": discovery_result.get("query_id"),
            "answer_length": len(final_answer),
            "citations_count": len(discovery_result.get("citations", [])),
            "search_results_count": len(discovery_result.get("search_results", []))
        }
        
        # 비동기 로깅 (실패해도 API 응답에 영향 없음)
        try:
            conversation_logger.log_conversation(
                session_id=session_id,
                user_question=userPrompt,
                ai_answer=final_answer,
                metadata=conversation_metadata
            )
        except Exception as e:
            logger.warning(f"대화 로깅 실패 (API 응답에는 영향 없음): {e}")
        
        # Firestore에 대화 저장 (비동기, 실패해도 API 응답에 영향 없음)
        try:
            # 프론트엔드에서 보낸 sessionId 사용, 없으면 Discovery Engine 세션 ID 사용
            frontend_session_id = sessionId.strip() if sessionId else ""
            firestore_session_id = frontend_session_id or get_short_session_id(session_id)
            
            await firestore_conversation.save_conversation(
                session_id=firestore_session_id,
                user_query=userPrompt,
                ai_response=final_answer,
                metadata=conversation_metadata
            )
        except Exception as e:
            logger.warning(f"Firestore 대화 저장 실패 (API 응답에는 영향 없음): {e}")

        return JSONResponse({
            "answer": final_answer,
            "summary_answer": final_answer,  # 기존 프론트엔드 호환성을 위해 추가
            "citations": discovery_result.get("citations", []),
            "search_results": discovery_result.get("search_results", []),
            "related_questions": discovery_result.get("related_questions", []),
            "updatedHistory": updated_history,
            "metadata": {
                "engine_type": "discovery_engine_main",
                "query_id": discovery_result.get("query_id"),
                "session_id": discovery_result.get("session_id")
            },
            "quality_check": {
                "has_answer": bool(final_answer and final_answer.strip()),
                "discovery_success": True
            }
        })

    except Exception as e:
        logger.exception(f"예상치 못한 오류 - 사용자 입력: {userPrompt}")
        # 에러 시에도 기본 답변 제공
        return JSONResponse({
            "answer": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            "summary_answer": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            "citations": [],
            "search_results": [],
            "related_questions": [],
            "updatedHistory": json.loads(conversationHistory),
            "metadata": {
                "engine_type": "error_fallback",
                "error": str(e)
            },
            "quality_check": {
                "has_answer": True,
                "discovery_success": False,
                "error": True
            }
        }, status_code=200)  # 200으로 반환하여 프론트엔드에서 오류 메시지 표시

@router.get("/gcs/{bucket_name}/{file_path:path}")
async def proxy_gcs_file(bucket_name: str, file_path: str):
    """GCS 파일 프록시 엔드포인트 - URL 디코딩 지원"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="스토리지 인증 실패")
    
    storage_client = get_storage_client()

    try:
        # URL 디코딩 처리 (한글 파일명 지원)
        import urllib.parse
        decoded_file_path = urllib.parse.unquote(file_path, encoding='utf-8')
        
        logger.info(f"GCS 파일 요청 - 원본: {file_path}, 디코딩: {decoded_file_path}")
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(decoded_file_path)
        
        if not blob.exists():
            # 원본 경로로도 시도
            blob = bucket.blob(file_path)
            if not blob.exists():
                logger.warning(f"파일 없음 - {bucket_name}/{decoded_file_path}")
                raise HTTPException(status_code=404, detail="파일 없음")

        def iterfile():
            with blob.open("rb") as f:
                yield from f

        content_type, _ = mimetypes.guess_type(decoded_file_path)
        content_type = content_type or "application/octet-stream"
        
        # 한글 파일명을 위한 Content-Disposition 헤더 설정
        filename = os.path.basename(decoded_file_path)
        encoded_filename = urllib.parse.quote(filename, encoding='utf-8')
        headers = {
            'Content-Disposition': f'inline; filename*=UTF-8\'\'{encoded_filename}'
        }
        
        return StreamingResponse(iterfile(), media_type=content_type, headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GCS 프록시 오류 - {bucket_name}/{file_path}", exc_info=True)
        raise HTTPException(status_code=500, detail="파일 읽기 실패")

@router.post('/api/discovery-answer')
async def discovery_answer(userPrompt: str = Form("")):
    """Discovery Engine Answer API 테스트 엔드포인트"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="서버 인증 실패 - Google Cloud 인증을 확인하세요")

    try:
        # Discovery Engine을 통한 답변 생성
        discovery_result = await get_complete_discovery_answer(userPrompt)
        
        logger.info(json.dumps({
            "stage": "discovery_answer_generated",
            "user_prompt": userPrompt,
            "answer_length": len(discovery_result.get("answer_text", "")),
            "citations_count": len(discovery_result.get("citations", [])),
            "search_results_count": len(discovery_result.get("search_results", []))
        }, ensure_ascii=False))

        return JSONResponse({
            "answer": discovery_result.get("answer_text", ""),
            "citations": discovery_result.get("citations", []),
            "search_results": discovery_result.get("search_results", []),
            "related_questions": discovery_result.get("related_questions", []),
            "metadata": {
                "query_id": discovery_result.get("query_id"),
                "session_id": discovery_result.get("session_id"),
                "engine_type": "discovery_engine_answer",
                "final_query_used": discovery_result.get("final_query_used", userPrompt)
            }
        })

    except Exception as e:
        logger.exception("Discovery Engine Answer API 오류")
        raise HTTPException(status_code=500, detail=f"Discovery Engine 답변 생성 실패: {str(e)}")

@router.post('/api/request-consultant')
async def request_consultant(
    userPrompt: str = Form(""), 
    conversationHistory: str = Form("[]"),
    sessionId: str = Form(""),
    sensitiveCategories: str = Form("[]")
):
    """상담사 연결 요청 엔드포인트"""
    try:
        conversation_history = json.loads(conversationHistory)
        sensitive_categories = json.loads(sensitiveCategories)
        
        # 상담 요청 생성 및 Google Chat 전송
        consultation_result = await consultant_service.create_consultation_request(
            user_query=userPrompt,
            conversation_history=conversation_history,
            session_id=sessionId or f"session_{datetime.now().timestamp()}",
            sensitive_categories=sensitive_categories
        )
        
        if consultation_result["success"]:
            logger.info(f"상담사 연결 요청 성공: {consultation_result['consultation_id']}")
            return JSONResponse({
                "success": True,
                "message": "상담사에게 문의가 전달되었습니다. 곧 연락드리겠습니다.",
                "consultation_id": consultation_result["consultation_id"],
                "timestamp": consultation_result["timestamp"]
            })
        else:
            logger.error(f"상담사 연결 요청 실패: {consultation_result}")
            return JSONResponse({
                "success": False,
                "message": "상담 요청 전송 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.",
                "error": consultation_result.get("error", "Unknown error")
            }, status_code=500)
            
    except Exception as e:
        logger.exception(f"상담사 연결 요청 처리 중 오류: {e}")
        return JSONResponse({
            "success": False,
            "message": "상담 요청 처리 중 오류가 발생했습니다.",
            "error": str(e)
        }, status_code=500)

@router.post('/api/request-demo')
async def request_demo(
    companyName: str = Form(""),
    customerName: str = Form(""), 
    email: str = Form(""),
    phone: str = Form(""),
    sendType: str = Form(""),
    usagePurpose: str = Form("")
):
    """데모 신청 엔드포인트"""
    try:
        # 데모 신청 데이터 구성
        demo_data = {
            "company_name": companyName.strip(),
            "customer_name": customerName.strip(),
            "email": email.strip(),
            "phone": phone.strip(),
            "send_type": sendType.strip(),
            "usage_purpose": usagePurpose.strip()
        }
        
        # 데모 신청 처리
        result = await demo_service.process_demo_request(demo_data)
        
        if result["success"]:
            logger.info(f"데모 신청 성공: {result['request_id']}")
            return JSONResponse({
                "success": True,
                "message": result["message"],
                "request_id": result["request_id"],
                "timestamp": result["timestamp"],
                "warnings": result.get("warnings", [])
            })
        else:
            logger.error(f"데모 신청 실패: {result}")
            status_code = 400 if result.get("errors") else 500
            return JSONResponse({
                "success": False,
                "message": result["message"],
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", [])
            }, status_code=status_code)
            
    except Exception as e:
        logger.exception(f"데모 신청 처리 중 오류: {e}")
        return JSONResponse({
            "success": False,
            "message": "데모 신청 처리 중 오류가 발생했습니다.",
            "error": str(e)
        }, status_code=500)

@router.post('/api/update-message-quality')
async def update_message_quality(
    session_id: str = Form(...),
    message_index: int = Form(...),
    rating: float = Form(...),
    feedback: str = Form("")
):
    """메시지 품질 평가 업데이트 엔드포인트"""
    try:
        success = await firestore_conversation.update_session_quality(
            session_id=session_id,
            message_index=message_index,
            quality_score=rating,
            feedback=feedback
        )
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "품질 평가가 저장되었습니다."
            })
        else:
            return JSONResponse({
                "success": False,
                "message": "품질 평가 저장에 실패했습니다."
            }, status_code=400)
            
    except Exception as e:
        logger.exception(f"품질 평가 업데이트 중 오류: {e}")
        return JSONResponse({
            "success": False,
            "message": "품질 평가 처리 중 오류가 발생했습니다.",
            "error": str(e)
        }, status_code=500)

@router.get('/api/conversation-history/{session_id}')
async def get_conversation_history(session_id: str, limit: int = 10):
    """대화 내역 조회 엔드포인트"""
    try:
        history = await firestore_conversation.get_conversation_history(
            session_id=session_id,
            limit=limit
        )
        
        return JSONResponse({
            "success": True,
            "session_id": session_id,
            "messages": history,
            "count": len(history)
        })
        
    except Exception as e:
        logger.exception(f"대화 내역 조회 중 오류: {e}")
        return JSONResponse({
            "success": False,
            "message": "대화 내역 조회 중 오류가 발생했습니다.",
            "error": str(e)
        }, status_code=500)

@router.get('/api/session-summary/{session_id}')
async def get_session_summary(session_id: str):
    """세션 요약 정보 조회 엔드포인트"""
    try:
        summary = await firestore_conversation.get_session_summary(session_id)
        
        if summary:
            return JSONResponse({
                "success": True,
                "summary": summary
            })
        else:
            return JSONResponse({
                "success": False,
                "message": "세션을 찾을 수 없습니다."
            }, status_code=404)
            
    except Exception as e:
        logger.exception(f"세션 요약 조회 중 오류: {e}")
        return JSONResponse({
            "success": False,
            "message": "세션 요약 조회 중 오류가 발생했습니다.",
            "error": str(e)
        }, status_code=500)

@router.get('/api/analytics')
async def get_analytics(days: int = 30):
    """대화 분석 데이터 조회 엔드포인트"""
    try:
        if days < 1 or days > 365:
            return JSONResponse({
                "success": False,
                "message": "날짜 범위는 1-365일 사이여야 합니다."
            }, status_code=400)
        
        analytics = await firestore_conversation.get_analytics_data(days=days)
        
        return JSONResponse({
            "success": True,
            "analytics": analytics
        })
        
    except Exception as e:
        logger.exception(f"분석 데이터 조회 중 오류: {e}")
        return JSONResponse({
            "success": False,
            "message": "분석 데이터 조회 중 오류가 발생했습니다.",
            "error": str(e)
        }, status_code=500)

@router.post('/api/cleanup-old-sessions')
async def cleanup_old_sessions(days_to_keep: int = Form(90)):
    """오래된 세션 정리 엔드포인트 (관리자용)"""
    try:
        if days_to_keep < 30:
            return JSONResponse({
                "success": False,
                "message": "최소 30일치 데이터는 보관해야 합니다."
            }, status_code=400)
        
        deleted_count = await firestore_conversation.cleanup_old_sessions(days_to_keep)
        
        return JSONResponse({
            "success": True,
            "message": f"{deleted_count}개의 오래된 세션이 정리되었습니다.",
            "deleted_count": deleted_count,
            "days_kept": days_to_keep
        })
        
    except Exception as e:
        logger.exception(f"세션 정리 중 오류: {e}")
        return JSONResponse({
            "success": False,
            "message": "세션 정리 중 오류가 발생했습니다.",
            "error": str(e)
        }, status_code=500)

