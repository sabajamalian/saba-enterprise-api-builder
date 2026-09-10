import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, field_serializer, field_validator

MONEY_PATTERN = r"^(?:[1-9][0-9]{0,8}(?:\.[0-9]{1,2})?|0\.(?:0[1-9]|[1-9][0-9]?))$"
MoneyString = Annotated[str, StringConstraints(pattern=MONEY_PATTERN)]


def decimal_string(value: object) -> object:
    if not isinstance(value, str) or re.fullmatch(MONEY_PATTERN, value) is None:
        raise ValueError("Amount must be a decimal string with at most two fractional digits.")
    return value


Money = Annotated[
    Decimal,
    Field(gt=0, le=Decimal("999999999.99"), max_digits=11, decimal_places=2),
    BeforeValidator(decimal_string, json_schema_input_type=MoneyString),
]


class PurchaseRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] = ""
    amount: Money = Field(description="Positive decimal string, up to 999999999.99; no binary floats.", examples=["125.50"])
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class PurchaseRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    amount: Decimal
    currency: str
    created_at: datetime

    @field_serializer("amount")
    def serialize_amount(self, amount: Decimal) -> str:
        return format(amount, ".2f")

    @field_validator("created_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class PurchaseRequestPage(BaseModel):
    items: list[PurchaseRequestRead]
    limit: int
    offset: int


class Health(BaseModel):
    status: str = "ok"


class ValidationIssue(BaseModel):
    path: list[str | int]
    code: str


class Problem(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    correlation_id: str
    errors: list[ValidationIssue] | None = None
