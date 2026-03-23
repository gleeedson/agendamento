import calendar
from datetime import date, datetime, time

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from agendamento.database import get_session
from agendamento.models import Agendamento, Pagamento, User
from agendamento.schemas import (
    AgendamentoAdminCriar,
    AgendamentoCriar,
    AgendamentoPublico,
    HorariosDisponiveis,
    Message,
    PagamentoPublico,
    PagamentoStatus,
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

dezembro = 12


def add_one_month(d: date) -> date:
    if d.month == dezembro:
        return d.replace(year=d.year + 1, month=1)
    else:
        days_in_month = calendar.monthrange(d.year, d.month + 1)[1]
        return d.replace(month=d.month + 1, day=min(d.day, days_in_month))


# Configurar CORS
origins = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:5500',
    'http://127.0.0.1:5500',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'https://agendamento-front.onrender.com',
    'https://690e0eee4a3e6a881385e8c2--bucolic-llama-3a585d.netlify.app/',
    'http://agendamento-front.onrender.com',
    'http://690e0eee4a3e6a881385e8c2--bucolic-llama-3a585d.netlify.app/',
    'https://front-pi-3.onrender.com',
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

    # Criar primeiro pagamento
    primeiro_pagamento = Pagamento(
        id_usuario=new_user.id,
        data_vencimento=add_one_month(date.today()),
        status='Em dia'
    )
    session.add(primeiro_pagamento)
    session.commit()

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
    # Verifica se o agendamento é no passado
    data_hora_agendamento = datetime.combine(
        agendamento.data,
        agendamento.hora
        )
    if data_hora_agendamento < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Não é possível criar agendamentos no passado',
        )

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


@app.get('/pagamento/status', response_model=PagamentoStatus)
def status_pagamento(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    pagamento = session.scalar(
        select(Pagamento)
        .where(Pagamento.id_usuario == user.id)
        .order_by(Pagamento.data_vencimento.desc())
    )
    if not pagamento:
        return {'status': 'Em dia', 'data_proximo_vencimento': None}

    status_atual = pagamento.status
    if status_atual == 'Em dia' and date.today() > pagamento.data_vencimento:
        status_atual = 'Atrasado'

    return {
        'status': status_atual,
        'data_proximo_vencimento': pagamento.data_vencimento
    }


@app.post('/pagamento/comprovante', response_model=Message)
def enviar_comprovante(
    arquivo: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    pagamento = session.scalar(
        select(Pagamento)
        .where(Pagamento.id_usuario == user.id)
        .order_by(Pagamento.data_vencimento.desc())
    )
    if not pagamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pagamento não encontrado"
            )

    arquivo_bytes = arquivo.file.read()
    pagamento.comprovante = arquivo_bytes
    pagamento.comprovante_mime = arquivo.content_type
    pagamento.status = 'Aguardando confirmação'
    session.commit()

    return {'message': 'Comprovante enviado com sucesso'}


# Rotas para o Adm
@app.get('/admin/usuarios', response_model=UserList)
def listar_usuarios(
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    usuarios = session.scalars(select(User)).all()
    resultado = []
    for u in usuarios:
        pagamento = session.scalar(
            select(Pagamento)
            .where(Pagamento.id_usuario == u.id)
            .order_by(Pagamento.data_vencimento.desc())
        )
        status_pag = None
        data_venc = None
        if pagamento:
            status_pag = pagamento.status
            if status_pag == 'Em dia' and date.today() > pagamento.data_vencimento:
                status_pag = 'Atrasado'
            data_venc = pagamento.data_vencimento

        u_obj = UserPublic.model_validate(u)
        u_obj.status_pagamento = status_pag
        u_obj.data_proximo_vencimento = data_venc
        resultado.append(u_obj)

    return {'users': resultado}


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

    # Criar primeiro pagamento
    primeiro_pagamento = Pagamento(
        id_usuario=new_user.id,
        data_vencimento=date.today(),
        status='Atrasado'
    )
    session.add(primeiro_pagamento)
    session.commit()

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


@app.post(
    '/admin/agendar',
    response_model=AgendamentoPublico,
    status_code=status.HTTP_201_CREATED,
)
def criar_agendamento_admin(
    agendamento: AgendamentoAdminCriar,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    # Verifica se o usuário existe
    user = session.scalar(select(User).where(
        User.id == agendamento.id_usuario
        ))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuário não encontrado',
        )

    # Verifica se o agendamento é no passado
    data_hora_agendamento = datetime.combine(
        agendamento.data,
        agendamento.hora
        )
    if data_hora_agendamento < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Não é possível criar agendamentos no passado',
        )

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

    return AgendamentoPublico(
        id=novo_agendamento.id,
        id_usuario=novo_agendamento.id_usuario,
        data=novo_agendamento.data,
        hora=novo_agendamento.hora,
        nome_usuario=user.nome,
    )


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


@app.get('/admin/usuarios/{user_id}/pagamentos',
         response_model=list[PagamentoPublico])
def listar_pagamentos_usuario(
    user_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    pagamentos = session.scalars(
        select(Pagamento)
        .where(Pagamento.id_usuario == user_id)
        .order_by(Pagamento.data_vencimento.desc())
    ).all()

    for p in pagamentos:
        if p.status == 'Em dia' and date.today() > p.data_vencimento:
            p.status = 'Atrasado'

    return pagamentos


@app.get('/admin/pagamentos/{pagamento_id}/comprovante')
def ver_comprovante(
    pagamento_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    pagamento = session.scalar(select(Pagamento).where(Pagamento.id == pagamento_id))
    if not pagamento or not pagamento.comprovante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprovante não encontrado"
            )

    return Response(
        content=pagamento.comprovante,
        media_type=pagamento.comprovante_mime or 'application/octet-stream'
        )


@app.patch('/admin/pagamentos/{pagamento_id}/aprovar', response_model=Message)
def aprovar_pagamento(
    pagamento_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    pagamento = session.scalar(
        select(Pagamento).where(Pagamento.id == pagamento_id)
        )
    if not pagamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pagamento não encontrado"
            )

    pagamento.status = 'Aprovado'

    mais_recente = session.scalar(
        select(Pagamento)
        .where(Pagamento.id_usuario == pagamento.id_usuario)
        .order_by(Pagamento.data_vencimento.desc())
    )
    if mais_recente and mais_recente.id == pagamento.id:
        novo_pag = Pagamento(
            id_usuario=pagamento.id_usuario,
            data_vencimento=add_one_month(pagamento.data_vencimento),
            status='Em dia'
        )
        session.add(novo_pag)

    session.commit()
    return {'message': 'Pagamento aprovado com sucesso'}


@app.patch('/admin/pagamentos/{pagamento_id}/recusar', response_model=Message)
def recusar_pagamento(
    pagamento_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    pagamento = session.scalar(select(Pagamento).where(Pagamento.id == pagamento_id))
    if not pagamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pagamento não encontrado"
            )

    pagamento.status = 'Atrasado'
    session.commit()
    return {'message': 'Pagamento recusado com sucesso'}
