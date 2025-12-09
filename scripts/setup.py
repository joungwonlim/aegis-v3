"""
AEGIS v3.0 - Setup Script
초기 데이터 설정
"""
from app.database import SessionLocal
from app.models import SystemConfig

def setup_initial_config():
    """시스템 초기 설정"""
    db = SessionLocal()

    configs = [
        ("AI_TRADING_ENABLED", "true", "AI 자동매매 활성화"),
        ("MAX_POSITION_SIZE", "0.1", "최대 포지션 비율 (10%)"),
        ("DAILY_LOSS_LIMIT", "-0.02", "일일 손실 한도 (-2%)"),
        ("TELEGRAM_NOTI", "true", "텔레그램 알림"),
        ("PORTFOLIO_MAX_LOSS", "-0.05", "포트폴리오 최대 손실 (-5%)"),
        ("POSITION_STOP_LOSS", "-0.03", "개별 종목 손절 (-3%)"),
        ("MAX_TRADES_PER_DAY", "20", "일일 최대 거래 횟수"),
        ("MAX_CONSECUTIVE_LOSSES", "3", "최대 연속 손실 횟수"),
    ]

    for key, value, description in configs:
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if not config:
            config = SystemConfig(key=key, value=value, description=description)
            db.add(config)
            print(f"✅ Added config: {key} = {value}")
        else:
            print(f"⏭️  Config already exists: {key}")

    db.commit()
    db.close()
    print("\n✅ Initial setup complete!")


if __name__ == "__main__":
    setup_initial_config()
