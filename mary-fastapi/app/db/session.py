from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# An empty URL must not crash import. Startup validation rejects it before serving.
_database_url = settings.DATABASE_URL or "mysql+aiomysql://unset:unset@127.0.0.1:1/unset"

engine = create_async_engine(
    _database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
