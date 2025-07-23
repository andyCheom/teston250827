"""텍스트 전처리 모듈"""
import re
import os
import logging
from typing import List, Set, Dict
from functools import lru_cache

# PyKoSpacing import
try:
    from pykospacing import Spacing
    KOSPACING_AVAILABLE = True
    # 전역 인스턴스 생성 (모델 로딩은 처음 한 번만)
    _spacing_model = None
except ImportError:
    KOSPACING_AVAILABLE = False
    print("⚠️ PyKoSpacing이 설치되지 않았습니다. 띄어쓰기 교정 기능이 비활성화됩니다.")

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def load_stopwords() -> Set[str]:
    """stopwords.txt에서 불용어 로드"""
    stopwords = set()
    stopwords_path = "stopwords.txt"
    
    try:
        with open(stopwords_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 주석 및 빈 줄 제외
                if line and not line.startswith('#'):
                    stopwords.add(line.lower())
        print(f"✅ 불용어 {len(stopwords)}개 로드 완료")
    except FileNotFoundError:
        print(f"⚠️ stopwords.txt 파일을 찾을 수 없습니다: {stopwords_path}")
    except Exception as e:
        print(f"❌ 불용어 로드 오류: {e}")
    
    return stopwords

def clean_text(text: str) -> str:
    """텍스트 정규화"""
    if not text:
        return ""
    
    # 특수문자 제거 (한글, 영문, 숫자, 공백만 유지)
    cleaned = re.sub(r'[^\w\sㄱ-ㅎㅏ-ㅣ가-힣]', ' ', text)
    
    # 연속된 공백을 하나로 변경
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned.strip()

def extract_keywords(text: str, min_length: int = 2, max_keywords: int = 10) -> List[str]:
    """키워드 추출 및 불용어 제거"""
    if not text or not text.strip():
        return []
    
    # 불용어 로드
    stopwords = load_stopwords()
    
    # 텍스트 정규화
    cleaned_text = clean_text(text)
    
    # 공백으로 분할
    tokens = cleaned_text.split()
    
    # 키워드 필터링
    keywords = []
    seen = set()
    
    for token in tokens:
        # 소문자로 변환하여 비교
        token_lower = token.lower()
        
        # 조건 검사
        if (len(token) >= min_length and  # 최소 길이
            token_lower not in stopwords and  # 불용어 제외
            token_lower not in seen):  # 중복 제거
            
            keywords.append(token)
            seen.add(token_lower)
            
            # 최대 개수 제한
            if len(keywords) >= max_keywords:
                break
    
    return keywords

def get_search_terms(user_prompt: str) -> List[str]:
    """검색에 적합한 키워드 추출"""
    # 1. 오타 수정 및 텍스트 정규화
    normalized_prompt = normalize_text_for_search(user_prompt)
    
    # 정규화 과정 로깅
    if normalized_prompt != user_prompt:
        print(f"🔧 텍스트 정규화: '{user_prompt}' → '{normalized_prompt}'")
    
    # 2. 기본 키워드 추출
    keywords = extract_keywords(normalized_prompt, min_length=2, max_keywords=8)
    
    # 3. 키워드가 너무 적으면 최소 길이를 줄여서 재시도
    if len(keywords) < 2:
        keywords = extract_keywords(normalized_prompt, min_length=1, max_keywords=8)
    
    # 4. 여전히 키워드가 없으면 정규화된 텍스트 사용
    if not keywords:
        keywords = [normalized_prompt.strip()] if normalized_prompt.strip() else [user_prompt.strip()]
    
    return keywords

@lru_cache(maxsize=100)
def get_typo_correction_patterns() -> Dict[str, str]:
    """오타 수정 패턴 반환"""
    return {
        # 한국어 흔한 오타
        r'어떡게': '어떻게',
        r'어떻해': '어떻게', 
        r'어캐': '어떻게',
        r'어뜨케': '어떻게',
        r'어떻개': '어떻게',
        r'않됨': '안돼',
        r'안됨': '안돼',
        r'되용': '되요',
        r'되여': '되어',
        r'해여': '해서',
        r'이써': '있어',
        r'업써': '없어',
        r'잇어': '있어',
        r'업어': '없어',
        r'사용방뻐': '사용방법',
        r'사용밥법': '사용방법',
        r'사용법': '사용방법',
        r'머야': '뭐야',
        r'모야': '뭐야',
        r'마이매일러': '마이메일러',
        r'매일러': '메일러',
        r'로긴': '로그인',
        r'로그인': '로그인',
        r'패스워드': '비밀번호',
        r'비번': '비밀번호',
        r'설치': '설치',
        r'셋팅': '설정',
        r'세팅': '설정',
        r'다운로드': '다운로드',
        r'업로드': '업로드',
        r'삭재': '삭제',
        
        # 영어 키보드 인접 오타
        r'\bteh\b': 'the',
        r'\bamd\b': 'and',
        r'\byuo\b': 'you', 
        r'\btaht\b': 'that',
        r'\bform\b': 'from',
        r'\bwith\b': 'with',
        
        # 중복 문자 정리
        r'([ㅋㅎ]){3,}': r'\1\1',  # ㅋㅋㅋㅋ → ㅋㅋ
        r'([a-zA-Z])\1{2,}': r'\1',  # helllllo → hello
        r'([!?.])\1{2,}': r'\1',     # !!!!! → !
        
        # 자모 분리 문제
        r'ㅜ{2,}': 'ㅜ',
        r'ㅠ{2,}': 'ㅠ',

        r'([ㅏ-ㅣㄱ-ㅎ])\1{1,}': r'\1' ,  # ㅛㅛ → ㅛ
        r'[ㅏ-ㅣㄱ-ㅎ]{2,}': '' 
    }

def fix_typos(text: str) -> str:
    """오타 수정"""
    if not text or not text.strip():
        return text
    
    patterns = get_typo_correction_patterns()
    corrected_text = text
    
    # 도메인 특화 용어 보호
    protected_terms = {
        '처음서비스', '처음소프트', '씨디엠소프트', '처음서베이',
        'API', 'UI', 'UX', 'DB', 'URL', 'IP', 'ID', 'GraphRAG'
    }
    
    # 보호할 용어들을 임시로 치환
    term_placeholders = {}
    for i, term in enumerate(protected_terms):
        if term in corrected_text:
            placeholder = f"__PROTECTED_TERM_{i}__"
            term_placeholders[placeholder] = term
            corrected_text = corrected_text.replace(term, placeholder)
    
    # 오타 수정 패턴 적용
    for pattern, replacement in patterns.items():
        try:
            corrected_text = re.sub(pattern, replacement, corrected_text, flags=re.IGNORECASE)
        except re.error:
            continue
    
    # 보호된 용어 복원
    for placeholder, term in term_placeholders.items():
        corrected_text = corrected_text.replace(placeholder, term)
    
    # 연속된 공백 정리
    corrected_text = re.sub(r'\s+', ' ', corrected_text).strip()
    
    return corrected_text

def normalize_text_for_search(text: str) -> str:
    """검색을 위한 텍스트 정규화 (띄어쓰기 교정 포함)"""
    if not text:
        return ""
    
    # 1. 띄어쓰기 교정 (가장 먼저 수행)
    spacing_corrected = smart_spacing_correction(text)
    
    # 2. 오타 수정
    typo_corrected = fix_typos(spacing_corrected)
    
    # 3. 특수문자 정리 (한글, 영문, 숫자, 공백만 유지)
    normalized = re.sub(r'[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ]', ' ', typo_corrected)
    
    # 4. 연속 공백 제거
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized

def get_spacing_model():
    """PyKoSpacing 모델 인스턴스 반환 (지연 로딩)"""
    global _spacing_model
    if _spacing_model is None and KOSPACING_AVAILABLE:
        try:
            logger.info("PyKoSpacing 모델 로딩 중...")
            _spacing_model = Spacing()
            logger.info("✅ PyKoSpacing 모델 로딩 완료")
        except Exception as e:
            logger.error(f"PyKoSpacing 모델 로딩 실패: {e}")
            return None
    return _spacing_model

def correct_spacing_with_kospacing(text: str) -> str:
    """PyKoSpacing을 사용한 띄어쓰기 교정"""
    if not text or not text.strip() or not KOSPACING_AVAILABLE:
        return text
    
    # 너무 긴 텍스트는 처리하지 않음 (성능 고려)
    if len(text) > 150:
        return text
    
    try:
        spacing_model = get_spacing_model()
        if spacing_model is None:
            return text
        
        # 띄어쓰기 교정 실행
        corrected_text = spacing_model(text)
        
        # 교정 결과 로깅
        if corrected_text != text:
            logger.info(f"📝 띄어쓰기 교정 (PyKoSpacing): '{text}' → '{corrected_text}'")
            print(f"📝 띄어쓰기 교정: '{text}' → '{corrected_text}'")
        
        return corrected_text
        
    except Exception as e:
        logger.warning(f"PyKoSpacing 띄어쓰기 교정 오류: {e} - 원본 텍스트 반환")
        return text

def smart_spacing_correction(text: str) -> str:
    """스마트한 띄어쓰기 교정 (로컬 규칙 + PyKoSpacing)"""
    if not text or not text.strip():
        return text
    
    # 1. 기본적인 로컬 띄어쓰기 규칙 적용 (빠른 전처리)
    corrected = text
    
    # 흔한 띄어쓰기 오류 패턴들 (검색 최적화용)
    spacing_patterns = {
        # 조사 분리 오류 수정
        r'([가-힣]) (이에요|예요|입니다|습니다|에요|이야)': r'\1\2',
        
        # 자주 발생하는 띄어쓰기 오류
        r'로그 ?인': '로그인',
        r'비밀 ?번호': '비밀번호',
        r'사용 ?방법': '사용방법',
        r'처음 ?서비스': '처음서비스',
        r'마이 ?메일러': '마이메일러',
        r'어떻 ?게': '어떻게',
        r'무엇 ?을': '무엇을',
        r'언제 ?부터': '언제부터',
        r'어디 ?서': '어디서',
        r'데이터 ?베이스': '데이터베이스',
        r'홈 ?페이지': '홈페이지',
        r'웹 ?사이트': '웹사이트',
        r'파일 ?업로드': '파일업로드',
        r'다운 ?로드': '다운로드',
        
        # 검색에 유리한 붙여쓰기
        r'할 ?수 ?있다': '할수있다',
        r'할 ?수 ?없다': '할수없다',
        r'되지 ?않는다': '되지않는다',
    }
    
    for pattern, replacement in spacing_patterns.items():
        corrected = re.sub(pattern, replacement, corrected)
    
    # 2. PyKoSpacing을 사용한 정밀 교정 (오프라인, 빠름)
    if len(corrected) <= 100:  # 적당한 길이의 텍스트만 처리
        kospacing_corrected = correct_spacing_with_kospacing(corrected)
        if kospacing_corrected and kospacing_corrected.strip():
            corrected = kospacing_corrected
    
    return corrected