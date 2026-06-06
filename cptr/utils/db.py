"""Async database engine and session management."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from cptr.env import DATA_DIR, DB_FILE

_engine = None
_async_session = None


def get_engine():
    global _engine
    if _engine is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _engine = create_async_engine(
            f"sqlite+aiosqlite:///{DB_FILE}",
            echo=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _async_session


async def get_db() -> AsyncSession:
    """Get an async DB session. Use as: async with await get_db() as db:"""
    factory = get_session_factory()
    return factory()


async def init_db():
    """Create tables and run Alembic migrations."""
    # Ensure WAL mode for concurrent reads
    async with get_engine().begin() as conn:
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")

    # Run Alembic migrations (sync, one-time startup cost)
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(Path(__file__).parent.parent / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{DB_FILE}")
    command.upgrade(alembic_cfg, "head")
