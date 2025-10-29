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
class AgendamentoCreate(BaseModel):
    data: date
    hora: time


class AgendamentoPublic(BaseModel):
    id: int
    usuario_id: int
    data: date
    hora: time
    usuario_nome: str
    model_config = ConfigDict(from_attributes=True)


class HorariosDisponiveis(BaseModel):
    data: date
    horarios_disponiveis: list[str]
