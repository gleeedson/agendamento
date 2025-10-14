import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from agendamento.app import app
from agendamento.database import get_session
from agendamento.models import User, table_registry


# O TestClient do FastAPI é uma classe para testar API
# que simula requisições HTTP sem a necessidade de iniciar o servidor
# Fixture, bloco de teste reutilizável
@pytest.fixture
def client(session):
    def get_session_override():
        return session

    with TestClient(app) as client:
        app.dependency_overrides[get_session] = get_session_override
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def session():
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )

    table_registry.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    table_registry.metadata.drop_all(engine)


@pytest.fixture
def user(session):
    user = User(
        username='Teste',
        email='teste@test.com',
        password='testtest',
        is_admin=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    return user
