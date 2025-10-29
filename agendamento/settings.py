from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8'
    )

    DATABASE_URL: str
    SECRET_KEY: str = 'sua_chave_secreta_super_segura_aqui'
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
