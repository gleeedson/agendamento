from pydantic import BaseModel, EmailStr


# Schemas = Contratos
class Message(BaseModel):
    message: str


# O json recebido por um endpoint é convertido em um objeto
class UserSchema(BaseModel):
    username: str
    email: EmailStr
    password: str


# Schema que não retorna senha
class UserPublic(BaseModel):
    username: str
    email: EmailStr
    id: int
    is_admin: bool


# usuário no DB
class UserDB(UserSchema):
    id: int
    is_admin: bool


class UserList(BaseModel):
    users: list[UserPublic]
