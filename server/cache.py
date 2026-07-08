import time
import asyncio
from typing import Any, Callable, TypeVar, Hashable

T = TypeVar("T")

class AsyncTTLCache:
    def __init__(self, ttl: int):
        self.ttl = ttl
        self.cache = {}
        self.locks = {}
        
    async def get_or_compute(self, key: Hashable, compute_func: Callable[..., Any], *args, **kwargs) -> T:
        now = time.time()
        
        
        if key in self.cache:
            value, expires_at = self.cache[key]
            if now < expires_at:
                return value
            else:
                del self.cache[key]
                
        
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
            
        async with self.locks[key]:
            
            if key in self.cache:
                value, expires_at = self.cache[key]
                if now < expires_at:
                    return value
                    
            
            result = await compute_func(*args, **kwargs)
            
            
            self.cache[key] = (result, time.time() + self.ttl)
            
        return result



cinemeta_cache = AsyncTTLCache(ttl=86400) 


search_cache = AsyncTTLCache(ttl=43200) 


stream_cache = AsyncTTLCache(ttl=14400) 
