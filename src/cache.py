"""캐싱 시스템 모듈"""
import time
import hashlib
from typing import Any, Optional

class MemoryCache:
    """메모리 기반 캐시 시스템"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        cache_entry = self.cache.get(key)
        if cache_entry and self.is_valid(key):
            return cache_entry['value']
        elif cache_entry:
            # 만료된 캐시 제거
            del self.cache[key]
        return None
        
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """캐시에 값 저장"""
        if len(self.cache) >= self.max_size:
            # LRU 방식으로 가장 오래된 항목 제거
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[key] = {
            'value': value,
            'expires': time.time() + ttl_seconds
        }
    
    def is_valid(self, key: str) -> bool:
        """캐시 유효성 검사"""
        if key not in self.cache:
            return False
        return time.time() < self.cache[key]['expires']
    
    def clear(self) -> None:
        """전체 캐시 초기화"""
        self.cache.clear()
    
    def size(self) -> int:
        """현재 캐시 크기"""
        return len(self.cache)

def get_cache_key(prefix: str, *args) -> str:
    """캐시 키 생성 유틸리티"""
    combined = f"{prefix}:{'|'.join(str(arg) for arg in args)}"
    return hashlib.md5(combined.encode()).hexdigest()

# 전역 캐시 인스턴스
memory_cache = MemoryCache()