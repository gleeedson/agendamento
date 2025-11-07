# Cria tabelas e admin

from sqlalchemy import select

from agendamento.database import create_tables, get_session
from agendamento.models import User


def create_admin():
    create_tables()

    session = next(get_session())

    # Verificar se já tem admin
    admin = session.scalar(select(User).where(User.email == 'admin@email.com'))

    if not admin:
        admin = User(
            nome='Admin',
            email='admin@email.com',
            senha='admin123',
            is_admin=True,
        )
        session.add(admin)
        session.commit()
        print('Usuário admin criado com sucesso!')
        print('Email: admin@email.com')
        print('Senha: admin123')
    else:
        print('Usuário admin já existe!')


if __name__ == '__main__':
    create_admin()
