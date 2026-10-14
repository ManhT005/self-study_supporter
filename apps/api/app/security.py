import hashlib
import secrets
import time
from collections import deque
from dataclasses import dataclass
from threading import Lock

from study_supporter.application.contracts.context import AppContext


@dataclass(frozen=True)
class Principal:
    context: AppContext
    username: str
    session_key: str


class Sessions:
    """Single-worker MVP. Only token hashes are held; restart revokes all sessions."""

    def __init__(self, ttl=8 * 3600, capacity=1000, clock=time.monotonic):
        self.ttl, self.capacity, self.clock = ttl, capacity, clock
        self.entries = {}
        self.lock = Lock()

    @staticmethod
    def key(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def issue(self, context, username):
        token = secrets.token_urlsafe(32)
        key = self.key(token)
        with self.lock:
            self.entries = {k: v for k, v in self.entries.items() if v[1] > self.clock()}
            if len(self.entries) >= self.capacity:
                raise OverflowError("Session capacity reached")
            self.entries[key] = (Principal(context, username, key), self.clock() + self.ttl)
        return token

    def get(self, token):
        if not token:
            return None
        key = self.key(token)
        with self.lock:
            value = self.entries.get(key)
            if value and value[1] > self.clock():
                return value[0]
            self.entries.pop(key, None)
        return None

    def revoke(self, token):
        with self.lock:
            self.entries.pop(self.key(token or ""), None)


class AuthLimiter:
    def __init__(self, limit=10, window=60, clock=time.monotonic):
        self.limit, self.window, self.clock = limit, window, clock
        self.entries, self.lock = {}, Lock()

    def allow(self, key):
        with self.lock:
            now = self.clock()
            self.entries = {
                k: deque(t for t in v if t > now - self.window)
                for k, v in self.entries.items()
                if v and v[-1] > now - self.window
            }
            if key not in self.entries and len(self.entries) >= 10000:
                return False
            attempts = self.entries.setdefault(key, deque())
            if len(attempts) >= self.limit:
                return False
            attempts.append(now)
            return True
