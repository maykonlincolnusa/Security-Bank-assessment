from __future__ import annotations

import redis.asyncio as redis


class InMemoryRedis:
    def __init__(self):
        self.store = {}
        self.counts = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.store[key] = value

    async def incr(self, key: str):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int):
        return True

    async def close(self):
        return True


def get_redis_client(redis_url: str):
    if redis_url.startswith("memory://"):
        return InMemoryRedis()
    return redis.from_url(redis_url, decode_responses=True)
