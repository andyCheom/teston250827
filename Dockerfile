# 1. 베이스 이미지 설정 (Python 3.11 슬림 버전)
# 가볍고 안정적인 파이썬 환경을 제공합니다.
FROM python:3.11-slim

# 2. 작업 디렉토리 설정
# 컨테이너 내에서 명령이 실행될 기본 경로입니다.
WORKDIR /usr/src/app

# 3. 의존성 설치
# requirements.txt를 먼저 복사하여
# 소스 코드가 변경되어도 불필요한 pip install을 방지합니다. (Docker 캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 개발 의존성 제거 (선택 사항 - 배포 환경에서는 불필요)
RUN pip uninstall --yes --quiet pip setuptools wheel  # pip, setuptools, wheel 제거

# 4. 애플리케이션 소스 코드 복사
COPY . . 

# 5. 애플리케이션 실행 명령어 (Gunicorn 사용)
# Cloud Run은 컨테이너가 8080 포트에서 수신 대기할 것으로 예상합니다.
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8080", "main:app"]

# 변경 사항 설명
# 1. CMD 명령어를 gunicorn 실행 명령어로 변경했습니다.
# 2. -w 4 옵션을 추가하여 4개의 워커 프로세스를 사용하도록 설정했습니다. (CPU 코어 수에 따라 조절 가능)
# 3. -k uvicorn.workers.UvicornWorker 옵션을 추가하여 uvicorn 워커를 사용하도록 지정했습니다. (FastAPI와 호환)
# 4. main:app -> main.py 파일의 app 객체를 실행하도록 변경했습니다. (FastAPI의 일반적인 구조)
