from __future__ import annotations

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover - exercised in lightweight local environments
    BaseSettings = None
    Field = None
    SettingsConfigDict = None


if BaseSettings is not None and Field is not None and SettingsConfigDict is not None:
    class TelegramBotCoreSettings(BaseSettings):
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")

        bot_token: str = Field(alias="TG_BOT_TOKEN")
        allowed_chat_ids: str = Field(default="", alias="TG_ALLOWED_CHAT_IDS")
        admin_chat_ids: str = Field(default="", alias="TG_ADMIN_CHAT_IDS")
        runtime_provider: str = Field(default="agent_os_python", alias="AG_RUNTIME_PROVIDER")
        runtime_profile: str = Field(default="zera-telegram-prod", alias="AG_RUNTIME_PROFILE")
        bot_mode: str = Field(default="polling", alias="TG_BOT_MODE")
        webhook_path_value: str = Field(default="/telegram/webhook", alias="TG_WEBHOOK_PATH")

        def chat_id_list(self, *, admins: bool = False) -> set[int]:
            raw = self.admin_chat_ids if admins else self.allowed_chat_ids
            values: set[int] = set()
            for part in raw.split(","):
                part = part.strip()
                if not part:
                    continue
                values.add(int(part))
            return values
else:
    class TelegramBotCoreSettings:
        def __init__(
            self,
            *,
            bot_token: str,
            allowed_chat_ids: str = "",
            admin_chat_ids: str = "",
            runtime_provider: str = "agent_os_python",
            runtime_profile: str = "zera-telegram-prod",
            bot_mode: str = "polling",
            webhook_path_value: str = "/telegram/webhook",
        ) -> None:
            self.bot_token = bot_token
            self.allowed_chat_ids = allowed_chat_ids
            self.admin_chat_ids = admin_chat_ids
            self.runtime_provider = runtime_provider
            self.runtime_profile = runtime_profile
            self.bot_mode = bot_mode
            self.webhook_path_value = webhook_path_value

        @classmethod
        def model_construct(cls, **kwargs: str) -> "TelegramBotCoreSettings":
            return cls(**kwargs)

        def chat_id_list(self, *, admins: bool = False) -> set[int]:
            raw = self.admin_chat_ids if admins else self.allowed_chat_ids
            values: set[int] = set()
            for part in raw.split(","):
                part = part.strip()
                if not part:
                    continue
                values.add(int(part))
            return values
