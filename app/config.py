from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "dev"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str

    BOT_TOKEN: str = ""              # Telegram bot token (for initData verification)
    FORWARD_BOT_TOKEN: str = ""      # token of the "second" bot to forward messages
    FORWARD_CHAT_ID: str | int = ""  # chat id to send notifications to

    CORS_ORIGINS: str = ""           # CSV list of allowed origins for CORS

    class Config:
        env_file = ".env"

settings = Settings()
