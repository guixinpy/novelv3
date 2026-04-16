class LRUCache:
    def __init__(self, max_size: int):
        self._cache: dict[str, object] = {}
        self._max_size = max_size

    def get(self, key: str):
        if key not in self._cache:
            return None
        value = self._cache.pop(key)
        self._cache[key] = value
        return value

    def set(self, key: str, value):
        if key in self._cache:
            self._cache.pop(key)
        elif len(self._cache) >= self._max_size:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = value


class CacheManager:
    def __init__(self):
        self.projects = LRUCache(100)
        self.chapters = LRUCache(50)
        self.ai_responses = LRUCache(200)
