import os

os.environ.setdefault("MCP_BEARER_TOKEN", "test-token")
os.environ.setdefault("LLM_PROVIDER", "seeded")
os.environ.setdefault(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000",
)

import pytest
from sqlmodel import Session, create_engine

from core_data_layer.seed import seed_data
from core_engine.services import OrchestrationService

@pytest.fixture
def engine():
    bind = create_engine("sqlite://", connect_args={"check_same_thread": False})
    seed_data(bind)
    return bind


@pytest.fixture
def session(engine):
    with Session(engine) as db:
        yield db


@pytest.fixture
def service(session) -> OrchestrationService:
    return OrchestrationService(session)
