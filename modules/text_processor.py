"""텍스트 전처리 모듈"""
import re
import logging
from typing import List, Set, Dict
from functools import lru_cache

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def load_stopwords() -> Set[str]:
    stopwords = set()
    stopwords_path = "stopwords.txt"
    
    try:
        with open(stopwords_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    stopwords.add(line.lower())
        print(f"✅ 불용어 {len(stopwords)}개 로드 완료")
    except FileNotFoundError:
        print(f"⚠️ stopwords.txt 파일을 찾을 수 없습니다: {stopwords_path}")
    except Exception as e:
        print(f"❌ 불용어 로드 오류: {e}")
    
    return stopwords

def clean_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r'[^\w\sㄱ-ㅎㅏ-ㅣ가-힣]', ' ', text)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def extract_keywords(text: str, min_length: int = 2, max_keywords: int = 10) -> List[str]:
    if not text or not text.strip():
        return []
    
    stopwords = load_stopwords()
    cleaned_text = clean_text(text)
    tokens = cleaned_text.split()

    keywords = []
    seen = set()
    
    for token in tokens:
        token_lower = token.lower()
        if (len(token) >= min_length and token_lower not in stopwords and token_lower not in seen):
            keywords.append(token)
            seen.add(token_lower)
            if len(keywords) >= max_keywords:
                break
    
    return keywords

def get_search_terms(user_prompt: str) -> List[str]:
    normalized_prompt = normalize_text_for_search(user_prompt)
    
    if normalized_prompt != user_prompt:
        print(f"🔧 텍스트 정규화: '{user_prompt}' → '{normalized_prompt}'")
    
    keywords = extract_keywords(normalized_prompt, min_length=2, max_keywords=8)
    if len(keywords) < 2:
        keywords = extract_keywords(normalized_prompt, min_length=1, max_keywords=8)
    if not keywords:
        keywords = [normalized_prompt.strip()] if normalized_prompt.strip() else [user_prompt.strip()]
    
    return keywords

@lru_cache(maxsize=100)
def get_typo_correction_patterns() -> Dict[str, str]:
    return {
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
        r'\bteh\b': 'the',
        r'\bamd\b': 'and',
        r'\byuo\b': 'you', 
        r'\btaht\b': 'that',
        r'\bform\b': 'from',
        r'\bwith\b': 'with',
        r'([ㅋㅎ]){3,}': r'\1\1',
        r'([a-zA-Z])\1{2,}': r'\1',
        r'([!?.])\1{2,}': r'\1',
        r'ㅜ{2,}': 'ㅜ',
        r'ㅠ{2,}': 'ㅠ',
        r'([ㅏ-ㅣㄱ-ㅎ])\1{1,}': r'\1',
        r'[ㅏ-ㅣㄱ-ㅎ]{2,}': '' 
    }

def fix_typos(text: str) -> str:
    if not text or not text.strip():
        return text

    patterns = get_typo_correction_patterns()
    corrected_text = text

    protected_terms = {
        '처음서비스', '처음소프트', '씨디엠소프트', '처음서베이',
        'API', 'UI', 'UX', 'DB', 'URL', 'IP', 'ID', 'GraphRAG'
    }
    term_placeholders = {}
    for i, term in enumerate(protected_terms):
        if term in corrected_text:
            placeholder = f"__PROTECTED_TERM_{i}__"
            term_placeholders[placeholder] = term
            corrected_text = corrected_text.replace(term, placeholder)

    for pattern, replacement in patterns.items():
        try:
            corrected_text = re.sub(pattern, replacement, corrected_text, flags=re.IGNORECASE)
        except re.error:
            continue

    for placeholder, term in term_placeholders.items():
        corrected_text = corrected_text.replace(placeholder, term)

    corrected_text = re.sub(r'\s+', ' ', corrected_text).strip()
    
    return corrected_text

def normalize_text_for_search(text: str) -> str:
    if not text:
        return ""
    
    spacing_corrected = basic_spacing_rules(text)
    typo_corrected = fix_typos(spacing_corrected)
    normalized = re.sub(r'[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ]', ' ', typo_corrected)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized

def basic_spacing_rules(text: str) -> str:
    """간단한 띄어쓰기 규칙만 적용 (PyKoSpacing 제거 버전)"""
    corrected = text

    spacing_patterns = {
        r'([가-힣]) (이에요|예요|입니다|습니다|에요|이야)': r'\1\2',
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
        r'할 ?수 ?있다': '할수있다',
        r'할 ?수 ?없다': '할수없다',
        r'되지 ?않는다': '되지않는다',
    }

    for pattern, replacement in spacing_patterns.items():
        corrected = re.sub(pattern, replacement, corrected)
    
    return corrected
