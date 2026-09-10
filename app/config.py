from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    database_url: str

    openai_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"

    input_price: float = 0.40
    output_price: float = 1.60

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()