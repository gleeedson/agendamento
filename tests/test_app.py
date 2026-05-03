from datetime import date, time
from http import HTTPStatus
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select

from agendamento import database, security
from agendamento.models import Agendamento, Pagamento, User
from agendamento.security import criar_token


def test_root_deve_retornar_ok_e_ola_mundo(client):
    response = client.get('/')

    assert response.status_code == HTTPStatus.OK

    assert response.json() == {'message': 'Olá Mundo!'}


def test_criar_usuario(client):
    response = client.post(
        '/registrar/',
        json={
            'nome': 'alice',
            'email': 'alice@example.com',
            'senha': 'secret',
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    # aceitar campos adicionais (por exemplo status_pagamento/data_proximo_vencimento)
    assert data['nome'] == 'alice'
    assert data['email'] == 'alice@example.com'
    assert data['id'] == 1
    assert data['is_admin'] is False


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
        json={'data': '2029-11-01', 'hora': '10:00:00'},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['data'] == '2029-11-01'
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
        data=date(2029, 11, 1),
        hora=time(10, 0),
    )
    agendamento2 = Agendamento(
        id_usuario=user.id,
        data=date(2029, 11, 2),
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


def test_exclusao_em_cascade(client, admin_token, session):
    # criar usuário com agendamento e pagamento

    user = User(nome='ToDelete', email='del@example.com', senha='x')
    session.add(user)
    session.commit()
    session.refresh(user)

    ag = Agendamento(id_usuario=user.id, data=date(2029, 12, 1), hora=time(9, 0))
    pag = Pagamento(
        id_usuario=user.id, data_vencimento=date(2029, 12, 1), status='Em dia'
        )
    session.add(ag)
    session.add(pag)
    session.commit()

    # delete via admin
    response = client.delete(
        f'/admin/usuarios/{user.id}',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert response.status_code == HTTPStatus.OK

    # verificar que agendamentos/pagamentos foram removidos
    a = session.scalar(select(Agendamento).where(Agendamento.id_usuario == user.id))
    p = session.scalar(select(Pagamento).where(Pagamento.id_usuario == user.id))
    assert a is None
    assert p is None


def test_status_pagamento_sem_pagamento(client, token, session):
    # criar usuário sem pagamentos

    u = User(nome='NoPay', email='nopay@example.com', senha='x')
    session.add(u)
    session.commit()
    session.refresh(u)

    # criar token para esse usuario

    t = criar_token({'user_id': u.id, 'email': u.email, 'is_admin': u.is_admin})

    response = client.get('/pagamento/status', headers={'Authorization': f'Bearer {t}'})
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['status'] == 'Em dia'


def test_enviar_comprovante_nao_encontrado(client, token):
    # tenta enviar comprovante quando não existe pagamento -> 404
    files = {'arquivo': ('test.txt', b'conteudo')}
    response = client.post(
        '/pagamento/comprovante',
        files=files, headers={'Authorization': f'Bearer {token}'}
        )
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_aprovar_pagamento_e_criar_proximo(client, admin_token, session):

    user = User(nome='Payer', email='payer@example.com', senha='x')
    session.add(user)
    session.commit()
    session.refresh(user)

    pag = Pagamento(
        id_usuario=user.id,
        data_vencimento=date(2025, 1, 1),
        status='Aguardando confirmação'
        )
    session.add(pag)
    session.commit()
    session.refresh(pag)

    response = client.patch(
        f'/admin/pagamentos/{pag.id}/aprovar',
        headers={'Authorization': f'Bearer {admin_token}'}
        )
    assert response.status_code == HTTPStatus.OK

    # o pagamento aprovado permanece e pode criar um novo se for o mais recente
    latest = session.scalar(
        select(Pagamento).where(Pagamento.id_usuario == user.id).order_by(
            Pagamento.data_vencimento.desc()
            )
            )
    assert latest is not None


def test_criar_verificar_token_invalido_e_expirado():
    payload = {'user_id': 1, 'email': 'x', 'is_admin': False}

    token = security.criar_token(payload)
    decoded = security.verificar_token(token)
    assert decoded['user_id'] == payload['user_id']

    with pytest.raises(HTTPException) as excinfo:
        security.verificar_token('not-a-token')
    assert 'Token inválido' in str(excinfo.value)

    # create an expired token by setting negative expiry hours
    orig = security.settings.ACCESS_TOKEN_EXPIRE_HOURS
    security.settings.ACCESS_TOKEN_EXPIRE_HOURS = -1
    try:
        expired = security.criar_token(payload)
        with pytest.raises(HTTPException) as ex2:
            security.verificar_token(expired)
        assert 'Token expirado' in str(ex2.value)
    finally:
        security.settings.ACCESS_TOKEN_EXPIRE_HOURS = orig


def test_dependencia_usuario_atual_e_admin(session, user):
    token = security.criar_token({
        'user_id': user.id,
        'email': user.email,
        'is_admin': user.is_admin,
    })
    creds = HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)

    current = security.get_current_user(creds, session)
    assert current.email == user.email

    with pytest.raises(HTTPException):
        security.get_current_admin(current)


def test_database_obter_sessao_e_criar_tabelas(monkeypatch):
    assert callable(database.get_session)

    called = {}

    def fake_create_all(engine):
        called['ok'] = True

    monkeypatch.setattr(database.table_registry.metadata, 'create_all',
                        fake_create_all)
    database.create_tables()
    assert called.get('ok', False)


def test_horarios_disponiveis_ignora_horario_ocupado(
    session, client, token, user
):
    d = date(2029, 11, 1)
    a = Agendamento(id_usuario=user.id, data=d, hora=time(10, 0))
    session.add(a)
    session.commit()

    resp = client.get(f'/horarios-disponiveis/{d.isoformat()}',
                      headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert '10:00' not in data['horarios_disponiveis']


def test_enviar_comprovante_atualiza_pagamento(session, client, token, user):
    p = Pagamento(id_usuario=user.id,
                  data_vencimento=date.today(), status='Em dia')
    session.add(p)
    session.commit()
    session.refresh(p)

    files = {'arquivo': ('receipt.txt', BytesIO(b'hi'))}
    resp = client.post('/pagamento/comprovante', files=files,
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == HTTPStatus.OK

    latest = session.scalar(select(Pagamento).where(Pagamento.id == p.id))
    assert latest is not None
    assert latest.status == 'Aguardando confirmação'
    assert latest.comprovante is not None

    comp = latest.comprovante
    if isinstance(comp, (bytes, bytearray)):
        comp = comp.decode()
    path = Path('.') / comp.lstrip('/')
    if path.exists():
        path.unlink()
