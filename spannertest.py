import os
import logging
from typing import List
from google.cloud import spanner
from google.oauth2 import service_account
from dotenv import load_dotenv

# 🔧 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 명확하게 .env 위치 지정
load_dotenv(dotenv_path="./.env")

class Config:
    SERVICE_ACCOUNT_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    PROJECT_ID = os.getenv("PROJECT_ID")
    SPANNER_INSTANCE_ID = os.getenv("SPANNER_INSTANCE_ID")
    SPANNER_DATABASE_ID = os.getenv("SPANNER_DATABASE_ID")
    SPANNER_TABLE_NAME = os.getenv("SPANNER_TABLE_NAME")

# 🔐 GCP 인증 및 클라이언트 초기화
try:
    if not os.path.exists(Config.SERVICE_ACCOUNT_PATH):
        raise FileNotFoundError(f"서비스 계정 키 파일이 존재하지 않습니다: {Config.SERVICE_ACCOUNT_PATH}")
    
    credentials = service_account.Credentials.from_service_account_file(
        Config.SERVICE_ACCOUNT_PATH,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    project_id = credentials.project_id or Config.PROJECT_ID

    # Spanner 클라이언트
    spanner_client = spanner.Client(credentials=credentials, project=project_id)

    logger.info(f"✅ 인증 성공 - project_id: {project_id}")
except Exception as e:
    logger.critical("❌ 인증 오류", exc_info=True)
    credentials = None
    spanner_client = None

# 📦 Spanner Triple 쿼리 함수
def query_spanner_triples(user_prompt: str) -> List[str]:
    if not spanner_client:
        logger.error("Spanner 클라이언트가 초기화되지 않았습니다.")
        return []

    try:
        instance = spanner_client.instance(Config.SPANNER_INSTANCE_ID)
        database = instance.database(Config.SPANNER_DATABASE_ID)

        query = f"""
        SELECT subject, predicate, object FROM `{Config.SPANNER_TABLE_NAME}`
        WHERE subject LIKE @term OR predicate LIKE @term OR object LIKE @term
        LIMIT 10
        """
        params = {"term": f"%{user_prompt}%"}
        param_types = {"term": spanner.param_types.STRING}

        with database.snapshot() as snapshot:
            results = snapshot.execute_sql(query, params=params, param_types=param_types)
            return [f"{row[0]} {row[1]} {row[2]}" for row in results]

    except Exception as e:
        logger.error("Spanner 쿼리 오류", exc_info=True)
        return []


# 명시적으로 환경변수 지정 (덮어쓰기)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = Config.SERVICE_ACCOUNT_PATH
# 🚀 테스트 실행
if __name__ == "__main__":
    test_prompt = "처음서비스"
    print(f"🔍 '{test_prompt}' 키워드로 Triple 조회 중...")

    triples = query_spanner_triples(test_prompt)

    if triples:
        print("✅ 쿼리 결과:")
        for t in triples:
            print(" -", t)
    else:
        print("⚠️ 결과 없음 또는 오류 발생")
