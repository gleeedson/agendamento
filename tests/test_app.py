from datetime import date, time
from http import HTTPStatus

from agendamento.models import Agendamento


def test_root_deve_retornar_ok_e_ola_mundo(client):
    response = client.get('/')

    assert response.status_code == HTTPStatus.OK

    assert response.json() == {'message': 'Olá Mundo!'}


def test_create_user(client):
    response = client.post(
        '/registrar/',
        json={
            'nome': 'alice',
            'email': 'alice@example.com',
            'senha': 'secret',
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {
        'nome': 'alice',
        'email': 'alice@example.com',
        'id': 1,
        'is_admin': False,
    }


def test_registrar_email_duplicado(client, user):
    response = client.post(
        '/registrar',
        json={
            'nome': 'Outro Usuario',
            'email': user.email,
            'senha': 'senha123',
        },
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {'detail': 'Email já cadastrado'}


def test_login_sucesso(client, user):
    response = client.post(
        '/login',
        json={'email': user.email, 'senha': user.senha},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert 'access_token' in data
    assert data['token_type'] == 'bearer'


def test_login_senha_incorreta(client, user):
    response = client.post(
        '/login',
        json={'email': user.email, 'senha': 'senha_errada'},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_criar_agendamento(client, token):
    response = client.post(
        '/agendar',
        json={'data': '2025-11-01', 'hora': '10:00:00'},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['data'] == '2025-11-01'
    assert data['hora'] == '10:00:00'


def test_listar_usuarios_admin(client, admin_token):
    response = client.get(
        '/admin/usuarios',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert 'users' in data


def test_listar_usuarios_nao_admin(client, token):
    response = client.get(
        '/admin/usuarios',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_remover_usuario(client, admin_token, user):
    response = client.delete(
        f'/admin/usuarios/{user.id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Usuário removido com sucesso'}


def test_listar_meus_agendamentos(client, token, session, user):
    # Criar agendamentos
    agendamento1 = Agendamento(
        id_usuario=user.id,
        data=date(2025, 11, 1),
        hora=time(10, 0),
    )
    agendamento2 = Agendamento(
        id_usuario=user.id,
        data=date(2025, 11, 2),
        hora=time(14, 0),
    )
    session.add(agendamento1)
    session.add(agendamento2)
    session.commit()

    response = client.get(
        '/meus-agendamentos',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
