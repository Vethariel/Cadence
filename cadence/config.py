from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    google_api_key: str
    gemini_model: str = "gemini-3.1-flash-lite"
    app_env: str = "development"


settings = Settings()
