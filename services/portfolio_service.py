"""
AEGIS v3.0 - Portfolio Service
포트폴리오 조회 전담 (Read Only)
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging

from app.database import SessionLocal
from app.models.account import Portfolio, AccountSnapshot

logger = logging.getLogger(__name__)


class PortfolioService:
    """
    Portfolio 조회 전담 (Read Only)

    모든 모듈은 이 서비스만 사용:
    - Dashboard
    - Brain
    - Telegram
    - Safety

    규칙: DB Write 절대 금지!
    """

    async def get_portfolio(self) -> List[Portfolio]:
        """
        전체 보유종목 조회

        Returns:
            보유 종목 리스트 (수량 > 0)
        """
        db: Session = SessionLocal()

        try:
            portfolio = db.query(Portfolio).filter(
                Portfolio.quantity > 0
            ).order_by(desc(Portfolio.profit_rate)).all()

            logger.debug(f"📊 Portfolio fetched: {len(portfolio)} stocks")

            return portfolio

        except Exception as e:
            logger.error(f"❌ Failed to get portfolio: {e}")
            return []
        finally:
            db.close()

    async def get_total_asset(self) -> int:
        """
        총 자산 조회 (최근 스냅샷)

        Returns:
            총 평가금액 (원)
        """
        db: Session = SessionLocal()

        try:
            snapshot = db.query(AccountSnapshot).order_by(
                desc(AccountSnapshot.timestamp)
            ).first()

            if snapshot:
                total = snapshot.total_asset
                logger.debug(f"💰 Total asset: {total:,}원")
                return total
            else:
                logger.warning("⚠️  No account snapshot found")
                return 0

        except Exception as e:
            logger.error(f"❌ Failed to get total asset: {e}")
            return 0
        finally:
            db.close()

    async def get_deposit(self) -> int:
        """
        예수금 조회 (최근 스냅샷)

        Returns:
            예수금 (원)
        """
        db: Session = SessionLocal()

        try:
            snapshot = db.query(AccountSnapshot).order_by(
                desc(AccountSnapshot.timestamp)
            ).first()

            if snapshot:
                deposit = snapshot.deposit
                logger.debug(f"💵 Deposit: {deposit:,}원")
                return deposit
            else:
                logger.warning("⚠️  No account snapshot found")
                return 0

        except Exception as e:
            logger.error(f"❌ Failed to get deposit: {e}")
            return 0
        finally:
            db.close()

    async def get_stock_info(self, stock_code: str) -> Optional[Portfolio]:
        """
        개별 종목 정보 조회

        Args:
            stock_code: 종목코드

        Returns:
            종목 정보 (없으면 None)
        """
        db: Session = SessionLocal()

        try:
            portfolio = db.query(Portfolio).filter(
                Portfolio.stock_code == stock_code
            ).first()

            if portfolio:
                logger.debug(f"📈 Stock info: {stock_code} {portfolio.quantity}주")
            else:
                logger.debug(f"⚠️  Stock not found: {stock_code}")

            return portfolio

        except Exception as e:
            logger.error(f"❌ Failed to get stock info: {e}")
            return None
        finally:
            db.close()

    async def get_portfolio_summary(self) -> dict:
        """
        포트폴리오 요약 정보

        Returns:
            {
                "total_stocks": int,      # 보유 종목 수
                "total_asset": int,       # 총 평가금액
                "deposit": int,           # 예수금
                "total_profit_rate": float # 총 수익률
            }
        """
        db: Session = SessionLocal()

        try:
            # 보유 종목
            portfolio = db.query(Portfolio).filter(
                Portfolio.quantity > 0
            ).all()

            # 계좌 스냅샷
            snapshot = db.query(AccountSnapshot).order_by(
                desc(AccountSnapshot.timestamp)
            ).first()

            summary = {
                "total_stocks": len(portfolio),
                "total_asset": snapshot.total_asset if snapshot else 0,
                "deposit": snapshot.deposit if snapshot else 0,
                "total_profit_rate": snapshot.total_return_rate if snapshot else 0.0
            }

            logger.debug(f"📊 Portfolio summary: {summary['total_stocks']} stocks, {summary['total_asset']:,}원")

            return summary

        except Exception as e:
            logger.error(f"❌ Failed to get portfolio summary: {e}")
            return {
                "total_stocks": 0,
                "total_asset": 0,
                "deposit": 0,
                "total_profit_rate": 0.0
            }
        finally:
            db.close()


# Singleton Instance
portfolio_service = PortfolioService()
