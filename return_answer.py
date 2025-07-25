from typing import List

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine

# 프로젝트 및 검색 설정
project_id = "cheom-kdb-test1"
location = "global"
engine_id = "test_1753406039510"
search_query = "처음서비스에 대해 알려줘"

def answer_query_sample(
    project_id: str,
    location: str,
    engine_id: str,
) -> discoveryengine.AnswerQueryResponse:
    # ✅ Discovery Engine API 엔드포인트 설정 (지역에 따라 다름)
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    # ✅ Conversational Search 클라이언트 생성
    client = discoveryengine.ConversationalSearchServiceClient(
        client_options=client_options
    )

    # ✅ Search Serving Config 리소스 경로 구성
    serving_config = f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/servingConfigs/default_serving_config"

    # ✅ (선택 사항) 사용자 질문에 대한 이해 설정
    query_understanding_spec = discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec(
        # 🔹 Query Rephraser 설정 (질문을 다시 표현)
        query_rephraser_spec=discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec.QueryRephraserSpec(
            disable=False,
            max_rephrase_steps=1,
        ),
        # 🔹 Query Classification 설정 (질문이 공격적인지, 의미 없는지 분류)
        query_classification_spec=discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec.QueryClassificationSpec(
            types=[
                discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec.QueryClassificationSpec.Type.ADVERSARIAL_QUERY,
                discoveryengine.AnswerQueryRequest.QueryUnderstandingSpec.QueryClassificationSpec.Type.NON_ANSWER_SEEKING_QUERY,
            ]
        ),
    )

    # ✅ (선택 사항) 응답 생성 설정
    answer_generation_spec = discoveryengine.AnswerQueryRequest.AnswerGenerationSpec(
        ignore_adversarial_query=False,           # 공격적인 질문 무시하지 않음
        ignore_non_answer_seeking_query=False,    # 의미 없는 질문도 처리
        ignore_low_relevant_content=False,        # 연관성 낮은 경우에도 fallback 응답 허용
        model_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.ModelSpec(
            model_version="gemini-2.0-flash-001/answer_gen/v1",  # 응답 생성에 사용할 모델
        ),
        prompt_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.PromptSpec(
            preamble="Give a detailed answer.",   # LLM에 줄 추가 지시문 (프롬프트 커스터마이징)
        ),
        include_citations=True,                   # 응답에 출처 포함 여부
        answer_language_code="en",                # 응답 언어 설정 (예: "ko"로 바꾸면 한국어로 응답)
    )

    # ✅ 요청 객체 생성
    request = discoveryengine.AnswerQueryRequest(
        serving_config=serving_config,  # 위에서 설정한 엔진 정보
        query=discoveryengine.Query(text="What is Vertex AI Search?"),  # 사용자의 질문
        session=None,  # 대화 세션 ID가 있다면 입력 (대화 이어가기 가능)
        query_understanding_spec=query_understanding_spec,  # 질문 이해 설정
        answer_generation_spec=answer_generation_spec,      # 응답 생성 설정
    )

    # ✅ API 호출
    response = client.answer_query(request)

    # ✅ 응답 출력
    print(response)

    return response
