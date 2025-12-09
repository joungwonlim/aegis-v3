"""
AEGIS v3.0 - Configuration Settings
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application Settings"""

    # App Info
    app_name: str = "AEGIS v3.0 API"
    app_version: str = "3.0.0"

    # Database
    database_url: str

    # KIS API
    kis_app_key: str
    kis_app_secret: str
    kis_account_number: str
    kis_account_code: str = "01"
    kis_account_no: str = ""  # Alternative format (with hyphen)
    kis_cano: str = ""  # Account number without product code
    kis_acnt_prdt_cd: str = "01"  # Account product code
    kis_paper_trading: bool = False
    kis_hts_id: str = ""  # HTS login ID for real-time notifications
    kis_ws_approval_key: str = ""  # Optional: WebSocket 사용 시 필요

    # KIS Trading Fees
    kis_fee_rate: float = 0.0140527  # 증권사 수수료 (%)
    kis_tax_total: float = 0.15  # 세금 (%)
    kis_nxt_fee_rate: float = 0.0139527  # NXT 수수료
    kis_nxt_tax_total: float = 0.15  # NXT 세금

    # AI Models
    anthropic_api_key: str
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    gemini_api_key: str

    # Data Sources
    dart_api_key: str

    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str

    # Trading Settings
    ai_trading_enabled: bool = True
    max_position_size: float = 0.1
    daily_loss_limit: float = -0.02

    # System
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
