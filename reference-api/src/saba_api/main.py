from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.exceptions import HTTPException as StarletteHTTPException

from saba_api.auth import IdentityUnavailable, InvalidCredentials, KeyStore, Principal, TokenVerifier
from saba_api.database import PurchaseRequest, create_database
from saba_api.errors import RequestBoundary, error_responses, http_error, validation_error
from saba_api.schemas import Health, PurchaseRequestCreate, PurchaseRequestPage, PurchaseRequestRead
from saba_api.settings import Settings

READ_SCOPE = "purchase-requests:read"
WRITE_SCOPE = "purchase-requests:write"
bearer = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    bearerFormat="JWT",
    description=(
        "Externally issued RS256 JWT. Read requires purchase-requests:read; create requires "
        "purchase-requests:write in the space-delimited scope claim. No token endpoint is provided."
    ),
)


def require_scope(required: str):
    def dependency(
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)],
    ) -> Principal:
        if credentials is None:
            raise HTTPException(401, headers={"WWW-Authenticate": "Bearer"})
        try:
            principal = request.app.state.verifier.verify(credentials.credentials)
        except InvalidCredentials:
            raise HTTPException(401, headers={"WWW-Authenticate": 'Bearer error="invalid_token"'}) from None
        except IdentityUnavailable:
            raise HTTPException(503, headers={"Retry-After": "30"}) from None
        if required not in principal.scopes:
            raise HTTPException(
                403, headers={"WWW-Authenticate": f'Bearer error="insufficient_scope", scope="{required}"'}
            )
        return principal

    return dependency


def get_session(request: Request):
    with request.app.state.sessions() as session:
        yield session


DatabaseSession = Annotated[Session, Depends(get_session)]
Reader = Annotated[Principal, Depends(require_scope(READ_SCOPE))]
Writer = Annotated[Principal, Depends(require_scope(WRITE_SCOPE))]


def create_app(settings: Settings | None = None, *, jwks_transport: httpx.BaseTransport | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        configuration = settings or Settings.from_env()
        # No auth-disabled fallback. Configuration and local key errors fail startup.
        with httpx.Client(
            timeout=httpx.Timeout(5.0, connect=2.0),
            follow_redirects=False,
            trust_env=False,
            transport=jwks_transport,
        ) as client:
            keys = KeyStore(configuration, client)
            engine = create_database(configuration.database_url)
            application.state.verifier = TokenVerifier(configuration, keys)
            application.state.sessions = sessionmaker(engine, expire_on_commit=False)
            application.state.engine = engine
            try:
                yield
            finally:
                engine.dispose()

    application = FastAPI(
        title="Saba Enterprise reference API",
        version="0.1.0",
        description="Runnable local reference for a hypothetical company, not a production procurement service.",
        lifespan=lifespan,
        responses=error_responses(401, 403, 404, 405, 422, 500, 503),
    )
    application.add_middleware(RequestBoundary)
    application.add_exception_handler(StarletteHTTPException, http_error)
    application.add_exception_handler(RequestValidationError, validation_error)

    @application.get("/health", response_model=Health, operation_id="getHealth")
    def health() -> Health:
        return Health()

    @application.post(
        "/api/v1/purchase-requests",
        response_model=PurchaseRequestRead,
        status_code=201,
        operation_id="createPurchaseRequest",
        description=f"Create a request owned by the verified subject. Requires `{WRITE_SCOPE}`.",
        openapi_extra={"x-required-scopes": [WRITE_SCOPE]},
    )
    def create_purchase_request(body: PurchaseRequestCreate, principal: Writer, session: DatabaseSession):
        record = PurchaseRequest(
            owner_id=principal.subject,
            title=body.title,
            description=body.description,
            amount_cents=int(body.amount * 100),
            currency=body.currency,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    @application.get(
        "/api/v1/purchase-requests",
        response_model=PurchaseRequestPage,
        operation_id="listPurchaseRequests",
        description=f"List only owned requests, ordered by created_at then id ascending. Requires `{READ_SCOPE}`.",
        openapi_extra={"x-required-scopes": [READ_SCOPE]},
    )
    def list_purchase_requests(
        principal: Reader,
        session: DatabaseSession,
        limit: Annotated[int, Query(ge=1, le=100)] = 25,
        offset: Annotated[int, Query(ge=0, le=9_223_372_036_854_775_807)] = 0,
    ):
        records = session.scalars(
            select(PurchaseRequest)
            .where(PurchaseRequest.owner_id == principal.subject)
            .order_by(PurchaseRequest.created_at.asc(), PurchaseRequest.id.asc())
            .limit(limit)
            .offset(offset)
        ).all()
        return PurchaseRequestPage(items=records, limit=limit, offset=offset)

    @application.get(
        "/api/v1/purchase-requests/{request_id}",
        response_model=PurchaseRequestRead,
        operation_id="getPurchaseRequest",
        description=f"Retrieve an owned request; other owners' IDs return 404. Requires `{READ_SCOPE}`.",
        openapi_extra={"x-required-scopes": [READ_SCOPE]},
    )
    def get_purchase_request(request_id: UUID, principal: Reader, session: DatabaseSession):
        record = session.scalar(
            select(PurchaseRequest).where(
                PurchaseRequest.id == str(request_id), PurchaseRequest.owner_id == principal.subject
            )
        )
        if record is None:
            raise HTTPException(404)
        return record

    return application


app = create_app()
