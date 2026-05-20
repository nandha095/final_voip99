from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Browser SIP Calling"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"
    allowed_origins: str = "http://localhost:8000"

    sip_domain: str = "pbx.example.com"
    sip_wss_url: str = "wss://pbx.example.com:8089/ws"
    sip_ws_url: str = "ws://pbx.example.com:8088/ws"
    sip_extension: str = "7001"
    sip_auth_username: str = "7001"
    sip_auth_password: str = "change-me"
    sip_display_name: str = "Browser Agent"

    asterisk_ami_enabled: bool = False
    asterisk_ami_host: str = "127.0.0.1"
    asterisk_ami_port: int = 5038
    asterisk_ami_username: str = "admin"
    asterisk_ami_secret: str = "super-secret"
    asterisk_ami_originate_context: str = "from-internal"
    asterisk_ami_originate_exten: str = "_X."
    asterisk_ami_originate_priority: int = 1
    asterisk_ami_originate_timeout_ms: int = 30000
    asterisk_ami_channel_prefix: str = "PJSIP"

    public_dial_prefix: str = ""

    def allowed_origins_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
