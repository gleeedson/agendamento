from datetime import date, time

from pydantic import BaseModel, ConfigDict, EmailStr


# Schemas = Contratos
class Message(BaseModel):
    message: str


# O json recebido por um endpoint é convertido em um objeto
class UserSchema(BaseModel):
    nome: str
    email: EmailStr
    senha: str


# Schema que não retorna senha
class UserPublic(BaseModel):
    id: int
    nome: str
    email: EmailStr
    is_admin: bool
    status_pagamento: str | None = None
    data_proximo_vencimento: date | None = None

    model_config = ConfigDict(from_attributes=True)


class UserList(BaseModel):
    users: list[UserPublic]


class UserLogin(BaseModel):
    email: EmailStr
    senha: str


# Token
class Token(BaseModel):
    access_token: str
    token_type: str


# Agendamento
class AgendamentoCriar(BaseModel):
    data: date
    hora: time


# Admin pode agendar aluno
class AgendamentoAdminCriar(BaseModel):
    id_usuario: int
    data: date
    hora: time


class AgendamentoPublico(BaseModel):
    id: int
    id_usuario: int
    data: date
    hora: time
    nome_usuario: str
    model_config = ConfigDict(from_attributes=True)


class HorariosDisponiveis(BaseModel):
    data: date
    horarios_disponiveis: list[str]


class PagamentoPublico(BaseModel):
    id: int
    id_usuario: int
    data_vencimento: date
    status: str

    model_config = ConfigDict(from_attributes=True)


class PagamentoStatus(BaseModel):
    status: str
    data_proximo_vencimento: date | None = None
