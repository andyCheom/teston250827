"""Triple 추출 및 검증 서비스"""
import re
import logging
from typing import Tuple

from .vertex_api import call_vertex_api

logger = logging.getLogger(__name__)

async def extract_triple_from_prompt(user_prompt: str) -> Tuple[str, str, str]:
    """사용자 프롬프트에서 Triple 추출"""
    prompt = f"""
사용자 질문을 분석하여 핵심 키워드를 (subject, predicate, object) triple로 추출해줘.

질문: "{user_prompt}"

추출 규칙:
- subject: 질문의 주요 대상 (제품명, 기능명 등)
- predicate: 관계나 동작 (사용법, 설정, 문제해결 등)  
- object: 구체적 속성이나 결과

응답 형식: subject=..., predicate=..., object=...

"""
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200}
    }

    response = await call_vertex_api(payload)
    text = response["candidates"][0]["content"]["parts"][0]["text"]

    # 정규표현식으로 추출
    match = re.search(r"subject\s*=\s*(.+?),\s*predicate\s*=\s*(.+?),\s*object\s*=\s*(.*)", text)
    if match:
        subject = match.group(1).strip()
        predicate = match.group(2).strip() 
        object_ = match.group(3).strip()
        
        # 무관한 질문 체크
        if subject == "IRRELEVANT":
            raise ValueError("질문이 처음서비스와 무관함")
            
        return subject, predicate, object_
    else:
        raise ValueError("Triple 추출 실패: " + text)