from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, Index, String, create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"
    __table_args__ = (Index("ix_purchase_requests_owner_created_id", "owner_id", "created_at", "id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    @property
    def amount(self) -> Decimal:
        return Decimal(self.amount_cents) / Decimal(100)


def create_database(url: str) -> Engine:
    database = make_url(url).database
    if database and database != ":memory:":
        Path(database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
        **({"poolclass": StaticPool} if database in (None, "", ":memory:") else {}),
    )
    Base.metadata.create_all(engine)
    return engine
