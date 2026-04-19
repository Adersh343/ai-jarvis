from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "llama3.2:latest"
    ollama_temperature: float = 0.75
    ollama_max_tokens: int = 512
    ollama_repeat_penalty: float = 1.2
    ollama_timeout: int = 30

    db_path: str = "memory.db"
    history_limit: int = 8
    history_window: int = 6

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
