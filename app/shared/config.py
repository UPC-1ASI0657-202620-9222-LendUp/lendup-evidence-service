from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    cloudinary_url: str = ""
    gemini_api_key: str = ""
    gemini_model: str = ""
    gemini_timeout_seconds: float = 20.0
    rabbitmq_url: str = ""
    rabbitmq_exchange: str = "lendup.domain.events"
    loans_service_url: str = ""
    loans_service_token: str = ""
    firebase_project_id: str = ""
