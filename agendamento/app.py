from datetime import date, time

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from agendamento.database import get_session
from agendamento.models import Agendamento, User
from agendamento.schemas import (
    AgendamentoCriar,
    AgendamentoPublico,
    HorariosDisponiveis,
    Message,
    Token,
    UserList,
    UserLogin,
    UserPublic,
    UserSchema,
)
from agendamento.security import (
    criar_token,
    get_current_admin,
    get_current_user,
)

app = FastAPI(title='API de agendamentos')


# Configurar CORS
origins = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:5500',
    'http://127.0.0.1:5500',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/', status_code=status.HTTP_200_OK, response_model=Message)
def read_root():
    return {'message': 'Olá Mundo!'}


# Rotas de cadastro e login
@app.post(
    '/registrar',
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
def registrar_usuario(
    usuario: UserSchema, session: Session = Depends(get_session)
):
    db_user = session.scalar(select(User).where(User.email == usuario.email))
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email já cadastrado',
        )

    new_user = User(
        nome=usuario.nome,
        email=usuario.email,
        senha=usuario.senha,
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    return new_user


@app.post('/login', response_model=Token)
def login(credenciais: UserLogin, session: Session = Depends(get_session)):
    user = session.scalar(select(User).where(User.email == credenciais.email))

    if not user or user.senha != credenciais.senha:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Email ou senha incorretos',
        )

    token = criar_token({
        'user_id': user.id,
        'email': user.email,
        'is_admin': user.is_admin,
    })

    return {'access_token': token, 'token_type': 'bearer'}


# Rotas dos alunos
@app.get('/horarios-disponiveis/{data}', response_model=HorariosDisponiveis)
def horarios_disponiveis(
    data: date,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    todos_horarios = [
        time(8, 0),
        time(9, 0),
        time(10, 0),
        time(11, 0),
        time(12, 0),
        time(13, 0),
        time(14, 0),
        time(15, 0),
        time(16, 0),
        time(17, 0),
    ]

    # verifica horários ocupados
    agendamentos = session.scalars(
        select(Agendamento).where(Agendamento.data == data)
    ).all()

    horarios_ocupados = [a.hora for a in agendamentos]
    horarios_livres = [h for h in todos_horarios if h not in horarios_ocupados]

    return {
        'data': data,
        'horarios_disponiveis': [h.strftime('%H:%M') for h in horarios_livres],
    }


@app.post(
    '/agendar',
    response_model=AgendamentoPublico,
    status_code=status.HTTP_201_CREATED,
)
def criar_agendamento(
    agendamento: AgendamentoCriar,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    # Verifica horário disponível
    existe = session.scalar(
        select(Agendamento).where(
            Agendamento.data == agendamento.data,
            Agendamento.hora == agendamento.hora,
        )
    )

    if existe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Horário indisponível',
        )

    # cria agendamento
    novo_agendamento = Agendamento(
        id_usuario=user.id,
        data=agendamento.data,
        hora=agendamento.hora,
    )
    session.add(novo_agendamento)
    session.commit()
    session.refresh(novo_agendamento)

    # mostra nome do aluno no agendamento
    return AgendamentoPublico(
        id=novo_agendamento.id,
        id_usuario=novo_agendamento.id_usuario,
        data=novo_agendamento.data,
        hora=novo_agendamento.hora,
        nome_usuario=user.nome,
    )


@app.get('/meus-agendamentos', response_model=list[AgendamentoPublico])
def listar_meus_agendamentos(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    agendamentos = session.scalars(
        select(Agendamento)
        .where(Agendamento.id_usuario == user.id)
        .order_by(Agendamento.data, Agendamento.hora)
    ).all()

    return [
        AgendamentoPublico(
            id=a.id,
            id_usuario=a.id_usuario,
            data=a.data,
            hora=a.hora,
            nome_usuario=user.nome,
        )
        for a in agendamentos
    ]


@app.delete('/cancelar-agendamento/{agendamento_id}', response_model=Message)
def cancelar_agendamento(
    agendamento_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    agendamento = session.scalar(
        select(Agendamento).where(
            Agendamento.id == agendamento_id,
            Agendamento.id_usuario == user.id,
        )
    )

    if not agendamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Agendamento não encontrado',
        )

    session.delete(agendamento)
    session.commit()

    return {'message': 'Agendamento cancelado com sucesso'}


# Rotas para o Adm
@app.get('/admin/usuarios', response_model=UserList)
def listar_usuarios(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    usuarios = session.scalars(select(User)).all()
    return {'users': usuarios}


@app.post(
    '/admin/usuarios',
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
def criar_usuario_admin(
    usuario: UserSchema,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    db_user = session.scalar(select(User).where(User.email == usuario.email))
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email já cadastrado',
        )

    new_user = User(
        nome=usuario.nome,
        email=usuario.email,
        senha=usuario.senha,
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    return new_user


@app.delete('/admin/usuarios/{user_id}', response_model=Message)
def remover_usuario_admin(
    user_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Não é possível remover a si mesmo',
        )

    user = session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuário não encontrado',
        )

    session.delete(user)
    session.commit()

    return {'message': 'Usuário removido com sucesso'}


@app.get('/admin/agendamentos', response_model=list[AgendamentoPublico])
def listar_todos_agendamentos(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    agendamentos = session.scalars(
        select(Agendamento).order_by(Agendamento.data, Agendamento.hora)
    ).all()

    result = []
    for a in agendamentos:
        user = session.scalar(select(User).where(User.id == a.id_usuario))
        result.append(
            AgendamentoPublico(
                id=a.id,
                id_usuario=a.id_usuario,
                data=a.data,
                hora=a.hora,
                nome_usuario=user.nome if user else 'Desconhecido',
            )
        )

    return result


@app.delete('/admin/agendamentos/{agendamento_id}', response_model=Message)
def remover_agendamento_admin(
    agendamento_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    agendamento = session.scalar(
        select(Agendamento).where(Agendamento.id == agendamento_id)
    )

    if not agendamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Agendamento não encontrado',
        )

    session.delete(agendamento)
    session.commit()

    return {'message': 'Agendamento removido com sucesso'}
