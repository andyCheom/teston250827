"""
GraphRAG 챗봇 API 메인 엔트리포인트
모듈화된 구조로 리팩토링됨
"""
import logging
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 로컬 모듈 import
from modules.auth import initialize_auth
from modules.routers.api import router

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="GraphRAG Chatbot API", 
    version="2.0.0",
    description="모듈화된 GraphRAG 기반 챗봇 API"
)

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 origin 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 인증 초기화
auth_success = initialize_auth()
if not auth_success:
    logger.error("❌ 인증 초기화 실패 - 서비스가 제대로 작동하지 않을 수 있습니다.")
else:
    logger.info("✅ 인증 초기화 성공")

# 라우터 등록
app.include_router(router)

# 정적 파일 서빙
@app.get("/")
async def serve_root():
    """루트 페이지 서빙"""
    return FileResponse("public/index.html")

# 정적 파일 마운트
app.mount("/", StaticFiles(directory="public"), name="static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """SPA 라우팅 처리"""
    import os
    from fastapi import HTTPException
    
    if full_path.startswith("api") or os.path.exists(os.path.join("public", full_path)):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse("public/index.html")
