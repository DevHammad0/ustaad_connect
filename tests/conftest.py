import sys
import os
import pytest
import asyncio
import math
from unittest.mock import MagicMock, AsyncMock

# Forcefully disable SQLite insert/update/delete RETURNING globally using a custom descriptor
from sqlalchemy.dialects.sqlite.base import SQLiteDialect
from sqlalchemy.dialects.sqlite.pysqlite import SQLiteDialect_pysqlite
from sqlalchemy.dialects.sqlite.aiosqlite import SQLiteDialect_aiosqlite

class ForceFalseDescriptor:
    def __get__(self, instance, owner):
        return False
    def __set__(self, instance, value):
        pass

SQLiteDialect.insert_returning = ForceFalseDescriptor()
SQLiteDialect.update_returning = ForceFalseDescriptor()
SQLiteDialect.delete_returning = ForceFalseDescriptor()

SQLiteDialect_pysqlite.insert_returning = ForceFalseDescriptor()
SQLiteDialect_pysqlite.update_returning = ForceFalseDescriptor()
SQLiteDialect_pysqlite.delete_returning = ForceFalseDescriptor()

SQLiteDialect_aiosqlite.insert_returning = ForceFalseDescriptor()
SQLiteDialect_aiosqlite.update_returning = ForceFalseDescriptor()
SQLiteDialect_aiosqlite.delete_returning = ForceFalseDescriptor()

# 1. Override environment variables BEFORE importing any app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["APP_SECRET"] = "test_app_secret"
os.environ["UPSTASH_REDIS_REST_URL"] = "https://mock-redis.upstash.io"
os.environ["UPSTASH_REDIS_REST_TOKEN"] = "mock_token"
os.environ["META_VERIFY_TOKEN"] = "ustaad_verify_token"

# 2. Mock upstash_redis (sync + async) before routes import it
#    RedisSession uses: lrange, rpush, rpop, hset, hsetnx, incr, expire, delete, ping, pipeline
class _MockPipeline:
    """Async-compatible pipeline that records and executes commands against MockRedis._store."""

    def __init__(self, store: dict) -> None:
        self._store = store
        self._cmds: list = []

    # Queue helpers used by RedisSession
    def hset(self, key, field, value):
        self._cmds.append(("hset", key, field, value)); return self

    def hsetnx(self, key, field, value):
        self._cmds.append(("hsetnx", key, field, value)); return self

    def rpush(self, key, *values):
        self._cmds.append(("rpush", key, *values)); return self

    def expire(self, key, ttl):
        self._cmds.append(("expire", key, ttl)); return self

    async def exec(self) -> list:
        return await self.execute()

    async def execute(self) -> list:
        results = []
        for cmd in self._cmds:
            op, key, *rest = cmd
            if op == "hset":
                self._store.setdefault(key, {})[rest[0]] = rest[1]
                results.append(1)
            elif op == "hsetnx":
                d = self._store.setdefault(key, {})
                if rest[0] not in d:
                    d[rest[0]] = rest[1]
                    results.append(1)
                else:
                    results.append(0)
            elif op == "rpush":
                self._store.setdefault(key, []).extend(rest)
                results.append(len(self._store[key]))
            elif op == "expire":
                results.append(1)
            else:
                results.append(None)
        self._cmds.clear()
        return results


class MockRedis:
    """Async-compatible in-memory Redis mock covering the full RedisSession surface."""
    _store: dict = {}

    def __init__(self, *args, **kwargs):
        pass

    # ---- sync helpers (used by geocoding.py) ----
    def get(self, key: str):
        val = self._store.get(key)
        if isinstance(val, list):
            return None  # Lists are not plain string keys
        return val

    def set(self, key: str, value, ex=None):
        self._store[key] = value
        return True

    @classmethod
    def from_env(cls, **_):
        return cls()

    # ---- async helpers (used by RedisSession) ----
    async def lrange(self, key: str, start: int, end: int):
        lst = self._store.get(key, [])
        if end == -1:
            return lst[start:]
        if end < 0:
            end = max(0, len(lst) + end + 1)
        return lst[start:end + 1]

    async def rpush(self, key: str, *values):
        self._store.setdefault(key, []).extend(values)
        return len(self._store[key])

    async def rpop(self, key: str):
        lst = self._store.get(key, [])
        if not lst:
            return None
        val = lst.pop()
        self._store[key] = lst
        return val

    async def incr(self, key: str) -> int:
        val = int(self._store.get(key, 0)) + 1
        self._store[key] = val
        return val

    async def delete(self, *keys):
        for k in keys:
            self._store.pop(k, None)
        return len(keys)

    async def ping(self) -> bool:
        return True

    def pipeline(self) -> _MockPipeline:
        return _MockPipeline(self._store)


import upstash_redis
import upstash_redis.asyncio as _upstash_async
upstash_redis.Redis = MockRedis
_upstash_async.Redis = MockRedis  # covers `from upstash_redis.asyncio import Redis`

# 3. Create async SQLite engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import StaticPool

# Setup in-memory SQLite engine
engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)

# Listen to connect event to register Postgres-equivalent functions in SQLite
from sqlalchemy import event
@event.listens_for(engine.sync_engine, "connect")
def register_sqlite_functions(dbapi_connection, connection_record):
    dbapi_connection.create_function("radians", 1, math.radians)
    dbapi_connection.create_function("cos", 1, math.cos)
    dbapi_connection.create_function("sin", 1, math.sin)
    dbapi_connection.create_function("acos", 1, lambda x: math.acos(max(-1.0, min(1.0, x))))
    dbapi_connection.create_function("GREATEST", -1, lambda *args: max(args))
    dbapi_connection.create_function("LEAST", -1, lambda *args: min(args))

# 4. Monkeypatch database.engine BEFORE any other module imports it
import src.api.database as db
db.engine = engine

from sqlmodel import SQLModel
from fastapi.testclient import TestClient

# 5. Mock external integrations (Nominatim geocoding & WhatsApp API)
@pytest.fixture(autouse=True)
def mock_external_apis(monkeypatch):
    # Mock geocoding to prevent Nominatim HTTP requests
    async def mock_reverse_geocode(lat: float, lng: float) -> dict:
        if 33.5 <= lat <= 33.8:
            slug = "islamabad"
        elif 31.4 <= lat <= 31.6:
            slug = "lahore"
        elif 24.8 <= lat <= 25.0:
            slug = "karachi"
        else:
            slug = "islamabad"
        return {"slug": slug, "city": slug.title()}

    monkeypatch.setattr("src.api.geocoding.reverse_geocode_city", mock_reverse_geocode)
    try:
        import src.api.routes.webhook as wh
        monkeypatch.setattr(wh, "reverse_geocode_city", mock_reverse_geocode)
    except (ImportError, AttributeError):
        pass
    try:
        import src.api.routes.customer as cust
        monkeypatch.setattr(cust, "reverse_geocode_city", mock_reverse_geocode)
    except (ImportError, AttributeError):
        pass
    try:
        import src.api.agent as ag
        monkeypatch.setattr(ag, "reverse_geocode_city", mock_reverse_geocode)
    except (ImportError, AttributeError):
        pass

    # Mock WhatsApp message sending to return True instantly
    async def mock_send_whatsapp(to_phone: str, message: str) -> bool:
        return True

    monkeypatch.setattr("src.api.whatsapp.send_whatsapp_message", mock_send_whatsapp)
    try:
        import src.api.routes.webhook as wh
        monkeypatch.setattr(wh, "send_whatsapp_message", mock_send_whatsapp)
    except (ImportError, AttributeError):
        pass
    try:
        import src.api.routes.customer as cust
        monkeypatch.setattr(cust, "send_whatsapp_message", mock_send_whatsapp)
    except (ImportError, AttributeError):
        pass

    # Mock WhatsApp location request sending to return True instantly
    async def mock_send_whatsapp_location_request(to_phone: str, body_text: str | None = None) -> bool:
        return True

    monkeypatch.setattr("src.api.whatsapp.send_whatsapp_location_request", mock_send_whatsapp_location_request)
    try:
        import src.api.routes.customer as cust
        monkeypatch.setattr(cust, "send_whatsapp_location_request", mock_send_whatsapp_location_request)
    except (ImportError, AttributeError):
        pass

    # Mock WhatsApp typing indicator sending to return True instantly
    async def mock_send_whatsapp_typing_indicator(message_id: str) -> bool:
        return True

    monkeypatch.setattr("src.api.whatsapp.send_whatsapp_typing_indicator", mock_send_whatsapp_typing_indicator)
    try:
        import src.api.routes.webhook as wh
        monkeypatch.setattr(wh, "send_whatsapp_typing_indicator", mock_send_whatsapp_typing_indicator)
    except (ImportError, AttributeError):
        pass

    # Patch the module-level _redis singletons so RedisSession never touches real Upstash
    mock_redis_instance = MockRedis()
    monkeypatch.setattr("src.api.routes.webhook._redis", mock_redis_instance)
    monkeypatch.setattr("src.api.routes.customer._redis", mock_redis_instance)

    # Mock Runner.run so customer chat tests don't hit real OpenAI endpoints
    class _MockResult:
        final_output = "Test response — mocked agent reply."

    async def mock_runner_run(*args, **kwargs):
        return _MockResult()

    monkeypatch.setattr("src.api.routes.customer.Runner.run", mock_runner_run)


# 6. Database session and table setup fixtures
@pytest.fixture(scope="function")
def db_setup():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Create tables + seed
    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        await db.seed_providers_if_empty()
        
    loop.run_until_complete(init_db())
    
    yield
    
    # Drop tables after test completes
    async def teardown_db():
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
            
    loop.run_until_complete(teardown_db())

import pytest_asyncio

@pytest_asyncio.fixture
async def session(db_setup) -> AsyncSession:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

# 7. Test client fixture
@pytest.fixture
def client(db_setup) -> TestClient:
    from src.api.main import app
    
    # Override get_session dependency
    async def override_get_session():
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
            
    app.dependency_overrides[db.get_session] = override_get_session
    
    with TestClient(app) as test_client:
        yield test_client
        
    app.dependency_overrides.clear()
