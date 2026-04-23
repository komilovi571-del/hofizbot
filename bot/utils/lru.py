"""
Oddiy TTL + bounded-LRU kesh (tashqi bog'liqliklarsiz).

In-memory callback store'lar uchun ishlatiladi: cheksiz xotira
o'sishining oldini oladi va eskirgan qiymatlarni avtomatik tashlaydi.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from threading import Lock
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    """Bounded LRU + TTL kesh. Thread-safe (sync lock)."""

    def __init__(self, maxsize: int = 10_000, ttl: float = 3600.0):
        self.maxsize = maxsize
        self.ttl = ttl
        self._data: "OrderedDict[K, tuple[V, float]]" = OrderedDict()
        self._lock = Lock()

    def __setitem__(self, key: K, value: V) -> None:
        now = time.monotonic()
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = (value, now + self.ttl)
            # LRU evict
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)

    def __getitem__(self, key: K) -> V:
        with self._lock:
            value, expires = self._data[key]
            if time.monotonic() > expires:
                del self._data[key]
                raise KeyError(key)
            self._data.move_to_end(key)
            return value

    def get(self, key: K, default: V | None = None) -> V | None:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: K) -> bool:
        return self.get(key) is not None

    def __len__(self) -> int:
        return len(self._data)

    def pop(self, key: K, default: V | None = None) -> V | None:
        with self._lock:
            item = self._data.pop(key, None)
            if item is None:
                return default
            value, expires = item
            if time.monotonic() > expires:
                return default
            return value
