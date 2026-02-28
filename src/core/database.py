from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from src.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)

    @classmethod
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"{cls.__name__.lower()}s"
