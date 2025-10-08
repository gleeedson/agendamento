import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from agendamento.app import app
from agendamento.models import table_registry


# O TestClient do FastAPI é uma classe para testar API
# que simula requisições HTTP sem a necessidade de iniciar o servidor
# Fixture, bloco de teste reutilizável
@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')

    table_registry.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    table_registry.metadata.drop_all(engine)
