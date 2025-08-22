"""
GraphRAG 챗봇 API 메인 엔트리포인트
모듈화된 구조로 리팩토링됨
테스트: 백엔드 배포 확인 v1.0
"""
import logging
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 로컬 모듈 import
from modules.auth import initialize_auth
from modules.routers.api import router
from modules.routers.discovery_only_api import router as discovery_router
from modules.routers.conversation_api import router as conversation_router

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
import os
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # 환경변수로 제어 가능
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# 인증 초기화 (백그라운드에서 진행 - 헬스 체크 블로킹 방지)
import asyncio
import threading

auth_success = False

def init_auth_background():
    """백그라운드에서 인증 초기화"""
    global auth_success
    try:
        auth_success = initialize_auth()
        if auth_success:
            logger.info("✅ 인증 초기화 성공")
        else:
            logger.error("❌ 인증 초기화 실패 - 서비스가 제대로 작동하지 않을 수 있습니다.")
    except Exception as e:
        logger.error(f"❌ 인증 초기화 중 예외 발생: {e}")
        auth_success = False

# 백그라운드 스레드에서 인증 초기화
auth_thread = threading.Thread(target=init_auth_background, daemon=True)
auth_thread.start()

# 헬스 체크용 인증 상태 확인 함수
def get_auth_status():
    """현재 인증 상태 반환"""
    return auth_success


# 라우터 등록
app.include_router(router)
app.include_router(discovery_router)

# 환경변수로 정적 파일 서빙 제어
import os
SERVE_STATIC = os.getenv("SERVE_STATIC", "true").lower() == "true"

# 위젯 전용 엔드포인트 (항상 활성화)
@app.get("/widget.js")
async def serve_widget_script():
    """임베드 가능한 위젯 스크립트 제공"""
    response = FileResponse("public/widget-embed.js", media_type="application/javascript")
    response.headers["Cache-Control"] = "public, max-age=3600"  # 1시간 캐시
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.get("/widget.html")
async def serve_widget_html():
    """위젯 HTML 파일 제공"""
    response = FileResponse("public/widget.html", media_type="text/html")
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.get("/widget-script.js")
async def serve_widget_script_js():
    """위젯 JavaScript 파일 제공"""
    response = FileResponse("public/widget-script.js", media_type="application/javascript")
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.get("/enhanced-chat.js")
async def serve_enhanced_chat_js():
    """Enhanced Chat JavaScript 파일 제공"""
    response = FileResponse("public/enhanced-chat.js", media_type="application/javascript")
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response






@app.get("/widget-style.css")
async def serve_widget_style_css():
    """위젯 CSS 파일 제공"""
    response = FileResponse("public/widget-style.css", media_type="text/css")
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.get("/widget-example")
async def serve_widget_example():
    """위젯 임베드 예제 페이지"""
    return FileResponse("public/embed-example.html")

if SERVE_STATIC:
    # 로컬 개발환경: 정적 파일 서빙
    @app.get("/")
    async def serve_root():
        
        """루트 페이지 서빙 (로컬 개발용)"""
        return FileResponse("public/index.html")

    # 정적 파일 마운트
    app.mount("/", StaticFiles(directory="public"), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA 라우팅 처리 (로컬 개발용)"""
        import os
        from fastapi import HTTPException
        
        if full_path.startswith("api") or os.path.exists(os.path.join("public", full_path)):
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse("public/index.html")
else:
    # Cloud Run 배포환경: API만 제공
    @app.get("/")
    async def api_info():
        """API 정보 반환 (배포환경용)"""
        return {
            "service": "GraphRAG Chatbot API",
            "version": "2.0.0",
            "status": "running",
            "frontend_url": "https://cheom-kdb-test1.web.app"
        }
    
    ## for test





