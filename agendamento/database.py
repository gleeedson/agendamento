from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from agendamento.models import table_registry
from agendamento.settings import Settings

settings = Settings()

engine_args = {}
if settings.DATABASE_URL.startswith('postgresql'):
    engine_args = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

engine = create_engine(settings.DATABASE_URL, **engine_args)


def get_session():
    with Session(engine) as session:
        yield session


def create_tables():
    table_registry.metadata.create_all(engine)
