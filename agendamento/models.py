from datetime import date, time

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, registry

table_registry = registry()


@table_registry.mapped_as_dataclass
class User:
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    nome: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    senha: Mapped[str]
    is_admin: Mapped[bool] = mapped_column(default=False)


@table_registry.mapped_as_dataclass
class Agendamento:
    __tablename__ = 'agendamentos'
    __table_args__ = (UniqueConstraint('data', 'hora'),)

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey('users.id'))
    data: Mapped[date]
    hora: Mapped[time]


@table_registry.mapped_as_dataclass
class Pagamento:
    __tablename__ = 'pagamentos'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey('users.id'))
    data_vencimento: Mapped[date]
    status: Mapped[str]
    # Status: 'Em dia', 'Atrasado', 'Aguardando confirmação', 'Aprovado', 'Recusado'
    comprovante: Mapped[bytes | None] = mapped_column(default=None)
    comprovante_mime: Mapped[str | None] = mapped_column(default=None)
