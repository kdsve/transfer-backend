from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # URL подключения к БД
    DATABASE_URL: str

    # Основной токен бота (для верификации initData)
    BOT_TOKEN: str | None = None

    # ⚡ ВРЕМЕННЫЙ ФЛАГ: отключение проверки initData
    # Если true → POST /transfers разрешается без проверки подписи Telegram
    SKIP_INITDATA_VERIFY: bool = False

    # Список доменов, которым разрешён доступ (через CORS)
    # Можно оставить пустым — тогда в main.py будет * (всё разрешено)
    CORS_ORIGINS: str = ""

    # Данные для пересылки заявок в Telegram-чат
    FORWARD_BOT_TOKEN: str | None = None
    FORWARD_CHAT_ID: str | None = None


# Экземпляр настроек (автоматически подтянет переменные из env)
settings = Settings()
