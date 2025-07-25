"""Triple 추출 및 검증 서비스"""
import re
import logging
from typing import Tuple

from .vertex_api import call_discovery_engine

logger = logging.getLogger(__name__)

def extract_triple_from_prompt(user_prompt: str) -> Tuple[str, str, str]:
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
    response = call_discovery_engine(prompt)
    text = response.get("answer_text", "")

    # JSON 형식이나 기존 형식 모두 처리
    import re
    import json
    
    # JSON 형식 시도
    try:
        # JSON 추출
        json_match = re.search(r'\{[^}]*\}', text)
        if json_match:
            json_data = json.loads(json_match.group())
            subject = json_data.get('subject', '').strip().strip('"')
            predicate = json_data.get('predicate', '').strip().strip('"')
            object_ = json_data.get('object', '').strip().strip('"')
            
            if subject and predicate and object_:
                # 무관한 질문 체크
                if subject == "IRRELEVANT":
                    raise ValueError("질문이 처음서비스와 무관함")
                return subject, predicate, object_
    except:
        pass
    
    # 기존 형식 시도
    match = re.search(r"subject\s*[=:]\s*(.+?)[,\n]\s*predicate\s*[=:]\s*(.+?)[,\n]\s*object\s*[=:]\s*(.*)", text, re.IGNORECASE)
    if match:
        subject = match.group(1).strip().strip('"')
        predicate = match.group(2).strip().strip('"')
        object_ = match.group(3).strip().strip('"')
        
        # 무관한 질문 체크
        if subject == "IRRELEVANT":
            raise ValueError("질문이 처음서비스와 무관함")
            
        return subject, predicate, object_
    else:
        raise ValueError("Triple 추출 실패: " + text)