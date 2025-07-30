# 1. 베이스 이미지 설정 (Python 3.11 슬림 버전)
# 가볍고 안정적인 파이썬 환경을 제공합니다.
FROM python:3.11-slim

# 2. 시스템 패키지 설치 (기본 의존성만)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
# 컨테이너 내에서 명령이 실행될 기본 경로입니다.
WORKDIR /usr/src/app

# 4. 의존성 설치
# requirements.txt를 먼저 복사하여
# 소스 코드가 변경되어도 불필요한 pip install을 방지합니다. (Docker 캐시 활용)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 개발 의존성 제거 (선택 사항 - 배포 환경에서는 불필요)
# RUN pip uninstall --yes --quiet setuptools wheel  # setuptools, wheel만 제거 (pip는 유지)

# 4. 백엔드 애플리케이션 소스 코드만 복사 (프런트엔드 제외)
COPY main.py .
COPY modules/ ./modules/
COPY prompt/ ./prompt/
COPY stopwords.txt . 

# 5. 포트 환경변수 설정 및 애플리케이션 실행 명령어
# Cloud Run은 컨테이너가 PORT 환경변수로 지정된 포트에서 수신 대기할 것으로 예상합니다.
ENV PORT=8080
EXPOSE $PORT
CMD exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT main:app