import requests
import json
import subprocess

# 1️⃣ GCP 액세스 토큰 획득 (로컬 gcloud 기반)
def get_access_token():
    result = subprocess.run(
        ["gcloud", "auth", "application-default", "print-access-token"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError("❌ 액세스 토큰 획득 실패")
    return result.stdout.strip()

# 2️⃣ Discovery Engine 검색 API 호출
def search_documents(query: str, token: str):
    url = "https://discoveryengine.googleapis.com/v1alpha/projects/580360941782/locations/global/collections/default_collection/engines/test_1753406039510/servingConfigs/default_search:search"

    payload = {
        "query": query,
        "pageSize": 10,
        "session": "projects/580360941782/locations/global/collections/default_collection/engines/test_1753406039510/sessions/-",
        "spellCorrectionSpec": {"mode": "AUTO"},
        "languageCode": "ko",
        "userInfo": {"timeZone": "Asia/Seoul"},
        "contentSearchSpec": {"snippetSpec": {"returnSnippet": True}}
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# 3️⃣ Answer API 호출 (search 결과 기반)
def generate_answer(query: str, query_id: str, session_id: str, token: str):
    url = "https://discoveryengine.googleapis.com/v1alpha/projects/580360941782/locations/global/collections/default_collection/engines/test_1753406039510/servingConfigs/default_search:answer"

    # 👇 promptSpec 생략 없이 원문 전체 사용
    prompt = '''"""
**"처음서비스"**는 처음소프트, 씨디엠소프트, 처음서베이로 구성된 종합 솔루션 기업이야.
너는 SaaS 솔루션 기업 **"처음서비스"**의 고객지원 담당자야.  
답변은 한국어로만 답변해.
---

...

이제 위 기준에 따라 고객의 질문에 대해 응답해줘.

"""'''

    payload = {
        "query": {
            "text": query,
            "queryId": query_id
        },
        "session": session_id,
        "relatedQuestionsSpec": {"enable": True},
        "answerGenerationSpec": {
            "ignoreAdversarialQuery": False,
            "ignoreNonAnswerSeekingQuery": False,
            "ignoreLowRelevantContent": True,
            "multimodalSpec": {"imageSource": "CORPUS_IMAGE_ONLY"},
            "includeCitations": True,
            "promptSpec": {"preamble": prompt},
            "modelSpec": {"modelVersion": "gemini-2.5-flash/answer_gen/v1"}
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# 🔄 전체 흐름 실행
if __name__ == "__main__":
    user_query = "마이메일러 사용법 알려줘"

    try:
        access_token = get_access_token()

        # 1. search API 호출
        search_result = search_documents(user_query, access_token)
        query_id = search_result.get("sessionInfo", {}).get("queryId")
        session_id = search_result.get("sessionInfo", {}).get("name")

        if not query_id or not session_id:
            raise ValueError("검색 결과에서 queryId 또는 session name 추출 실패")

        print(f"🔍 Query ID: {query_id}")
        print(f"🧾 Session ID: {session_id}")

        # 2. answer API 호출
        answer_result = generate_answer(user_query, query_id, session_id, access_token)
        print("📄 생성된 답변:")
        print(json.dumps(answer_result, indent=2, ensure_ascii=False))

    except Exception as e:
        print("❌ 오류 발생:", e)
