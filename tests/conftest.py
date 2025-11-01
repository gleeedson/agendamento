import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from agendamento.app import app
from agendamento.database import get_session
from agendamento.models import User, table_registry
from agendamento.security import criar_token


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
        nome='Teste',
        email='teste@test.com',
        senha='testtest',
        is_admin=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    return user


@pytest.fixture
def admin_user(session):
    admin = User(
        nome='Admin User',
        email='admin@example.com',
        senha='admin123',
        is_admin=True,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


@pytest.fixture
def token(user):
    return criar_token({
        'user_id': user.id,
        'email': user.email,
        'is_admin': user.is_admin,
    })


@pytest.fixture
def admin_token(admin_user):
    return criar_token({
        'user_id': admin_user.id,
        'email': admin_user.email,
        'is_admin': admin_user.is_admin,
    })
