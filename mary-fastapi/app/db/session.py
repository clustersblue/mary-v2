import ssl

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

_SSL_QUERY_KEYS = (
    "ssl_ca",
    "ssl_cert",
    "ssl_key",
    "ssl_check_hostname",
    "ssl_verify_cert",
    "ssl_verify_identity",
    "ssl_mode",
    "ssl-mode",
)


def database_connection(url: str):
    """Return a database URL and driver arguments.

    A certificate path in the URL is turned into an SSL context. The async
    MySQL driver cannot use the certificate dictionary that the URL parameter
    would otherwise produce.
    """
    parsed = make_url(url)
    ca_file = parsed.query.get("ssl_ca")
    if isinstance(ca_file, (tuple, list)):
        ca_file = ca_file[0] if ca_file else None
    if not ca_file:
        return parsed, {}

    context = ssl.create_default_context(cafile=str(ca_file))
    # The private DigitalOcean hostname is not always listed on the certificate.
    # The certificate authority is still verified.
    context.check_hostname = False
    context.verify_mode = ssl.CERT_REQUIRED
    return parsed.difference_update_query(_SSL_QUERY_KEYS), {"ssl": context}


# An empty URL must not crash import. Startup validation rejects it before serving.
_database_url, _connect_args = database_connection(
    settings.DATABASE_URL or "mysql+aiomysql://unset:unset@127.0.0.1:1/unset"
)

engine = create_async_engine(
    _database_url,
    connect_args=_connect_args,
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
