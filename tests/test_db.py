from dataclasses import asdict

from sqlalchemy import select

from agendamento.models import User


def test_create_user(session):
    new_user = User(
        username='alice', password='secret', email='teste@test', is_admin=False
    )

    session.add(new_user)
    session.commit()

    # scalar transforma tudo que retorna do banco em um objeto python
    user = session.scalar(select(User).where(User.username == 'alice'))

    assert asdict(user) == {
        'id': 1,
        'username': 'alice',
        'password': 'secret',
        'email': 'teste@test',
        'is_admin': False,
    }
