# Backend Micro Optimization (백엔드 미세 최적화)

> **"로그로 학습하고, 실패를 싸게 막아라"**

---

## 📋 목차

1. [학습 기반 최적화](#1-학습-기반-최적화)
2. [SAFE MODE 시스템](#2-safe-mode-시스템)
3. [Database 스키마](#3-database-스키마)
4. [구현 코드](#4-구현-코드)

---

## 1. 학습 기반 최적화

### 1.1 개념

**핵심 아이디어:**
```
매 주문마다 로그를 남기고
→ 분석해서
→ 종목별 최적 파라미터 자동 조정
```

**학습 항목:**
- 스프레드 크기별 최적 전략
- 대기 시간별 체결률
- 시간대별 체결 확률
- 종목별 패턴

### 1.2 학습 프로세스

```
┌─────────────────────────────────────────────────────────────┐
│          학습 기반 주문 최적화 시스템                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [매 주문마다]                                              │
│  ┌──────────────────────────────────────────┐               │
│  │  1. 주문 전 상태 기록                     │               │
│  │     • 스프레드: 5bp                      │               │
│  │     • 선택: Maker + 10초 대기            │               │
│  └──────────────────────────────────────────┘               │
│                 ↓                                           │
│  ┌──────────────────────────────────────────┐               │
│  │  2. 주문 실행                             │               │
│  │     • 매수 1호가 지정가 주문              │               │
│  │     • 10초 대기                           │               │
│  └──────────────────────────────────────────┘               │
│                 ↓                                           │
│  ┌──────────────────────────────────────────┐               │
│  │  3. 결과 기록                             │               │
│  │     • 체결 여부: True                     │               │
│  │     • 체결가: bid                         │               │
│  │     • 절약: 5bp                           │               │
│  │     • 최종 수익률: +2.3%                  │               │
│  └──────────────────────────────────────────┘               │
│                 ↓                                           │
│          micro_opt_logs 테이블 저장                          │
│                                                             │
│  [주기적 분석: 매일 23:00]                                   │
│  ┌──────────────────────────────────────────┐               │
│  │  종목별 통계 분석                         │               │
│  │                                          │               │
│  │  삼성전자:                                │               │
│  │  • 스프레드 < 3bp → Taker 권장           │               │
│  │  • 스프레드 > 10bp → Maker + 10초        │               │
│  │  • 점심시간 → 체결률 30% (대기 20초)     │               │
│  └──────────────────────────────────────────┘               │
│                 ↓                                           │
│  ┌──────────────────────────────────────────┐               │
│  │  파라미터 자동 조정                       │               │
│  │                                          │               │
│  │  stock_order_config 테이블 UPDATE        │               │
│  │  • 005930: wait=10, spread_min=10        │               │
│  └──────────────────────────────────────────┘               │
│                 ↓                                           │
│          다음 주문부터 자동 적용!                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 효과

| 항목 | 기존 | 학습 후 | 개선 |
|-----|------|---------|------|
| 체결률 | 70% | 85% | +15% |
| 평균 절약 | 0.12% | 0.18% | +0.06% |
| 연간 수익 | 120만원 | 180만원 | **+60만원** |

---

## 2. SAFE MODE 시스템

### 2.1 개념

**핵심 아이디어:**
```
시스템 이상 감지 시
→ 자동으로 SAFE MODE 진입
→ 추가 손실 방지
```

**3가지 모드:**

```
┌─────────────────────────────────────────────────────────────┐
│                  시스템 동작 모드                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [NORMAL MODE] 정상 운영                                    │
│  ──────────────────────────────────────────────────────    │
│  • 신규 매수: ✅ 허용                                        │
│  • 추가 매수: ✅ 허용                                        │
│  • 매도: ✅ 정상 실행                                        │
│  • 피라미딩: ✅ 허용                                         │
│                                                             │
│  [SAFE MODE] 안전 모드                                      │
│  ──────────────────────────────────────────────────────    │
│  • 신규 매수: ❌ 금지                                        │
│  • 추가 매수: ❌ 금지                                        │
│  • 매도: ✅ 정상 실행 (손절/익절)                            │
│  • 피라미딩: ❌ 금지                                         │
│                                                             │
│  진입 조건:                                                 │
│  • API 에러 연속 3회                                        │
│  • DB 연결 실패                                             │
│  • 당일 손실 -3% 초과                                       │
│  • WebSocket 연결 끊김 5분 이상                             │
│                                                             │
│  [HALT MODE] 긴급 정지                                      │
│  ──────────────────────────────────────────────────────    │
│  • 신규 매수: ❌ 금지                                        │
│  • 추가 매수: ❌ 금지                                        │
│  • 매도: ⚠️ 수동 승인 필요                                  │
│  • 피라미딩: ❌ 금지                                         │
│                                                             │
│  진입 조건:                                                 │
│  • 당일 손실 -5% 초과                                       │
│  • 시스템 크래시 감지                                       │
│  • 수동 HALT 명령                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 모드 전환 흐름

```
    NORMAL
      │
      │ ← API 에러 3회
      ↓
    SAFE ────┐
      │      │ ← 30분 정상 → 복구
      │      ↓
      │   NORMAL
      │
      │ ← 손실 -5% 초과
      ↓
    HALT
      │
      │ ← 수동 해제만 가능
      ↓
    NORMAL
```

---

## 3. Database 스키마

### 3.1 micro_opt_logs (미세 최적화 로그)

```sql
-- 매 주문마다 최적화 정보 기록
CREATE TABLE micro_opt_logs (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    order_type VARCHAR(10) NOT NULL,  -- BUY, SELL
    strategy VARCHAR(20),              -- MAKER, TAKER

    -- 주문 전 상태
    spread_bp INT,                     -- 스프레드 (basis point, 1bp = 0.01%)
    bid_price INT,
    ask_price INT,
    time_of_day TIME,                  -- 주문 시간

    -- 주문 파라미터
    wait_seconds INT DEFAULT 0,        -- 대기 시간
    order_price INT,                   -- 주문가
    order_qty INT,                     -- 주문 수량

    -- 결과
    filled BOOLEAN DEFAULT FALSE,      -- 체결 여부
    filled_price INT,                  -- 체결가
    filled_time TIMESTAMP,             -- 체결 시간
    saved_bp INT,                      -- 절약한 bp (basis point)

    -- 최종 성과 (매도 시 업데이트)
    final_pnl_bp INT,                  -- 최종 손익 (bp)
    holding_days INT,                  -- 보유 기간

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_micro_logs_stock ON micro_opt_logs(stock_code, created_at DESC);
CREATE INDEX idx_micro_logs_spread ON micro_opt_logs(spread_bp, strategy);
CREATE INDEX idx_micro_logs_time ON micro_opt_logs(time_of_day, filled);
```

### 3.2 stock_order_config (종목별 최적 설정)

```sql
-- 학습된 종목별 최적 파라미터
CREATE TABLE stock_order_config (
    stock_code VARCHAR(20) PRIMARY KEY,

    -- Maker 전략 파라미터
    maker_spread_min_bp INT DEFAULT 5,      -- Maker 최소 스프레드 (5bp)
    maker_wait_seconds INT DEFAULT 10,      -- Maker 대기 시간
    maker_success_rate FLOAT DEFAULT 0.7,   -- Maker 체결률

    -- Taker 전략
    taker_spread_max_bp INT DEFAULT 3,      -- Taker 최대 스프레드 (3bp)

    -- 시간대별 조정
    lunch_wait_multiplier FLOAT DEFAULT 2.0,  -- 점심시간 대기 시간 배수

    -- 학습 메타
    sample_count INT DEFAULT 0,             -- 학습 샘플 수
    last_analyzed_at TIMESTAMP,
    confidence_score FLOAT DEFAULT 0.5,     -- 신뢰도 (0~1)

    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 3.3 system_mode (시스템 모드)

```sql
-- 시스템 동작 모드 관리
CREATE TABLE system_mode (
    id INT PRIMARY KEY DEFAULT 1,  -- 싱글톤
    mode VARCHAR(20) NOT NULL DEFAULT 'NORMAL',  -- NORMAL, SAFE, HALT

    -- 모드 전환 사유
    reason TEXT,
    triggered_by VARCHAR(50),         -- API_ERROR, DB_ERROR, LOSS_LIMIT, MANUAL

    -- 에러 카운터
    api_error_count INT DEFAULT 0,
    db_error_count INT DEFAULT 0,
    ws_disconnected_minutes INT DEFAULT 0,

    -- 당일 손실
    today_loss_pct FLOAT DEFAULT 0.0,

    -- 모드 시작 시간
    mode_started_at TIMESTAMP DEFAULT NOW(),
    mode_changed_at TIMESTAMP DEFAULT NOW(),

    updated_at TIMESTAMP DEFAULT NOW(),

    -- 1개 row만 허용
    CONSTRAINT single_row CHECK (id = 1)
);

-- 초기 데이터
INSERT INTO system_mode (id, mode) VALUES (1, 'NORMAL')
ON CONFLICT (id) DO NOTHING;
```

---

## 4. 구현 코드

### 4.1 Micro Opt Logger

```python
# brain/micro_opt_logger.py
"""
Micro Optimization Logger
매 주문마다 최적화 정보 기록 및 학습
"""

from typing import Dict, Optional
from datetime import datetime, time
from database.models import SessionLocal


class MicroOptLogger:
    """
    미세 최적화 로거

    매 주문마다:
    1. 주문 전 상태 기록
    2. 결과 기록
    3. 주기적 분석 → 파라미터 자동 조정
    """

    def __init__(self):
        self.db = SessionLocal()

    def log_order_attempt(
        self,
        stock_code: str,
        order_type: str,
        bid_price: int,
        ask_price: int,
        strategy: str,
        wait_seconds: int
    ) -> int:
        """
        주문 시도 기록

        Returns:
            log_id (나중에 결과 업데이트용)
        """
        spread_bp = int((ask_price - bid_price) / bid_price * 10000)  # basis point

        log_entry = {
            'stock_code': stock_code,
            'order_type': order_type,
            'strategy': strategy,
            'spread_bp': spread_bp,
            'bid_price': bid_price,
            'ask_price': ask_price,
            'time_of_day': datetime.now().time(),
            'wait_seconds': wait_seconds,
            'order_price': bid_price if strategy == 'MAKER' else ask_price,
        }

        # DB 저장
        result = self.db.execute(
            """
            INSERT INTO micro_opt_logs
            (stock_code, order_type, strategy, spread_bp, bid_price, ask_price,
             time_of_day, wait_seconds, order_price)
            VALUES
            (:stock_code, :order_type, :strategy, :spread_bp, :bid_price, :ask_price,
             :time_of_day, :wait_seconds, :order_price)
            RETURNING id
            """,
            log_entry
        )
        self.db.commit()

        log_id = result.scalar()
        return log_id

    def log_order_result(
        self,
        log_id: int,
        filled: bool,
        filled_price: Optional[int] = None
    ):
        """주문 결과 업데이트"""
        if filled and filled_price:
            saved_bp = self.calculate_saved_bp(log_id, filled_price)

            self.db.execute(
                """
                UPDATE micro_opt_logs
                SET filled = :filled,
                    filled_price = :filled_price,
                    filled_time = NOW(),
                    saved_bp = :saved_bp,
                    updated_at = NOW()
                WHERE id = :log_id
                """,
                {
                    'log_id': log_id,
                    'filled': filled,
                    'filled_price': filled_price,
                    'saved_bp': saved_bp,
                }
            )
        else:
            self.db.execute(
                """
                UPDATE micro_opt_logs
                SET filled = :filled,
                    updated_at = NOW()
                WHERE id = :log_id
                """,
                {'log_id': log_id, 'filled': filled}
            )

        self.db.commit()

    def calculate_saved_bp(self, log_id: int, filled_price: int) -> int:
        """절약한 bp 계산"""
        log = self.db.execute(
            "SELECT ask_price FROM micro_opt_logs WHERE id = :log_id",
            {'log_id': log_id}
        ).fetchone()

        if log and log['ask_price']:
            saved = int((log['ask_price'] - filled_price) / filled_price * 10000)
            return saved

        return 0

    def analyze_and_optimize(self, stock_code: str):
        """
        종목별 최적 파라미터 분석

        최근 30일 데이터 기반 학습
        """
        # 최근 30일 로그 조회
        logs = self.db.execute(
            """
            SELECT
                spread_bp,
                strategy,
                wait_seconds,
                filled,
                saved_bp
            FROM micro_opt_logs
            WHERE stock_code = :stock_code
              AND created_at >= NOW() - INTERVAL '30 days'
            """,
            {'stock_code': stock_code}
        ).fetchall()

        if len(logs) < 10:
            return  # 샘플 부족

        # 전략별 통계
        maker_stats = [log for log in logs if log['strategy'] == 'MAKER']
        taker_stats = [log for log in logs if log['strategy'] == 'TAKER']

        # Maker 체결률
        maker_fill_rate = (
            sum(1 for log in maker_stats if log['filled']) / len(maker_stats)
            if maker_stats else 0
        )

        # Maker 평균 절약
        maker_avg_saved = (
            sum(log['saved_bp'] for log in maker_stats if log['filled']) / len([l for l in maker_stats if l['filled']])
            if maker_stats else 0
        )

        # 최적 스프레드 임계값 계산
        optimal_spread = self._find_optimal_spread(logs)

        # stock_order_config 업데이트
        self.db.execute(
            """
            INSERT INTO stock_order_config
            (stock_code, maker_spread_min_bp, maker_success_rate, sample_count, last_analyzed_at)
            VALUES
            (:stock_code, :spread_min, :success_rate, :count, NOW())
            ON CONFLICT (stock_code)
            DO UPDATE SET
                maker_spread_min_bp = :spread_min,
                maker_success_rate = :success_rate,
                sample_count = :count,
                last_analyzed_at = NOW(),
                confidence_score = LEAST(1.0, :count / 100.0)
            """,
            {
                'stock_code': stock_code,
                'spread_min': optimal_spread,
                'success_rate': maker_fill_rate,
                'count': len(logs),
            }
        )
        self.db.commit()

    def _find_optimal_spread(self, logs: list) -> int:
        """최적 스프레드 임계값 찾기"""
        # 스프레드별 체결률 분석
        spread_groups = {}

        for log in logs:
            spread = log['spread_bp']
            filled = log['filled']

            bucket = (spread // 5) * 5  # 5bp 단위로 그룹핑

            if bucket not in spread_groups:
                spread_groups[bucket] = {'total': 0, 'filled': 0}

            spread_groups[bucket]['total'] += 1
            if filled:
                spread_groups[bucket]['filled'] += 1

        # 체결률 70% 이상인 최소 스프레드
        for spread in sorted(spread_groups.keys()):
            fill_rate = spread_groups[spread]['filled'] / spread_groups[spread]['total']

            if fill_rate >= 0.7:
                return spread

        return 10  # 기본값


# 싱글톤
_micro_opt_logger: Optional[MicroOptLogger] = None


def get_micro_opt_logger() -> MicroOptLogger:
    global _micro_opt_logger
    if _micro_opt_logger is None:
        _micro_opt_logger = MicroOptLogger()
    return _micro_opt_logger
```

### 4.2 SAFE MODE Manager

```python
# utils/safe_mode.py
"""
SAFE MODE Manager
시스템 이상 감지 및 자동 보호
"""

from typing import Optional
from datetime import datetime, timedelta
from database.models import SessionLocal


class SafeModeManager:
    """
    시스템 모드 관리자

    NORMAL → SAFE → HALT
    """

    def __init__(self):
        self.db = SessionLocal()
        self.current_mode = self.get_current_mode()

    def get_current_mode(self) -> str:
        """현재 모드 조회"""
        result = self.db.execute(
            "SELECT mode FROM system_mode WHERE id = 1"
        ).fetchone()

        return result['mode'] if result else 'NORMAL'

    def can_place_new_order(self) -> bool:
        """신규 주문 가능 여부"""
        mode = self.get_current_mode()

        if mode == 'NORMAL':
            return True
        elif mode == 'SAFE':
            return False  # 신규 매수 금지
        elif mode == 'HALT':
            return False  # 모든 매수 금지

        return False  # 알 수 없는 모드 → 안전하게 금지

    def report_api_error(self, error_type: str):
        """API 에러 보고"""
        # 에러 카운터 증가
        self.db.execute(
            """
            UPDATE system_mode
            SET api_error_count = api_error_count + 1,
                updated_at = NOW()
            WHERE id = 1
            """
        )
        self.db.commit()

        # 연속 3회 에러 → SAFE MODE
        count = self.db.execute(
            "SELECT api_error_count FROM system_mode WHERE id = 1"
        ).scalar()

        if count >= 3:
            self.enter_safe_mode('API 에러 연속 3회 발생')

    def report_db_error(self):
        """DB 에러 보고"""
        # 즉시 SAFE MODE
        self.enter_safe_mode('데이터베이스 연결 오류')

    def report_daily_loss(self, loss_pct: float):
        """당일 손실 보고"""
        self.db.execute(
            """
            UPDATE system_mode
            SET today_loss_pct = :loss_pct,
                updated_at = NOW()
            WHERE id = 1
            """,
            {'loss_pct': loss_pct}
        )
        self.db.commit()

        # 손실 -3% → SAFE MODE
        if loss_pct <= -3.0:
            self.enter_safe_mode(f'당일 손실 {loss_pct:.2f}% 도달')

        # 손실 -5% → HALT MODE
        if loss_pct <= -5.0:
            self.enter_halt_mode(f'당일 손실 {loss_pct:.2f}% 위험 수준')

    def enter_safe_mode(self, reason: str):
        """SAFE MODE 진입"""
        self.db.execute(
            """
            UPDATE system_mode
            SET mode = 'SAFE',
                reason = :reason,
                triggered_by = 'AUTO',
                mode_started_at = NOW(),
                mode_changed_at = NOW()
            WHERE id = 1
            """,
            {'reason': reason}
        )
        self.db.commit()

        # 텔레그램 알림
        from services.telegram_commander import send_alert
        send_alert(f'🟡 SAFE MODE 진입\n사유: {reason}\n\n신규 매수 금지!')

        print(f'🟡 SAFE MODE 진입: {reason}')

    def enter_halt_mode(self, reason: str):
        """HALT MODE 진입"""
        self.db.execute(
            """
            UPDATE system_mode
            SET mode = 'HALT',
                reason = :reason,
                triggered_by = 'AUTO',
                mode_started_at = NOW(),
                mode_changed_at = NOW()
            WHERE id = 1
            """,
            {'reason': reason}
        )
        self.db.commit()

        # 텔레그램 긴급 알림
        from services.telegram_commander import send_alert
        send_alert(f'🔴 HALT MODE 진입!\n사유: {reason}\n\n모든 매매 중지!')

        print(f'🔴 HALT MODE: {reason}')

    def try_auto_recovery(self):
        """자동 복구 시도 (30분 정상 시)"""
        mode_info = self.db.execute(
            "SELECT mode, mode_started_at, api_error_count FROM system_mode WHERE id = 1"
        ).fetchone()

        if mode_info['mode'] != 'SAFE':
            return

        # 30분 경과 + 에러 없음 → NORMAL 복구
        elapsed = datetime.now() - mode_info['mode_started_at']

        if elapsed > timedelta(minutes=30) and mode_info['api_error_count'] == 0:
            self.exit_safe_mode('30분 정상 운영 확인')

    def exit_safe_mode(self, reason: str):
        """SAFE MODE 종료"""
        self.db.execute(
            """
            UPDATE system_mode
            SET mode = 'NORMAL',
                reason = :reason,
                api_error_count = 0,
                db_error_count = 0,
                mode_changed_at = NOW()
            WHERE id = 1
            """,
            {'reason': reason}
        )
        self.db.commit()

        print(f'✅ NORMAL MODE 복구: {reason}')

    def manual_reset(self):
        """수동 리셋 (HALT → NORMAL)"""
        self.db.execute(
            """
            UPDATE system_mode
            SET mode = 'NORMAL',
                reason = '수동 리셋',
                triggered_by = 'MANUAL',
                api_error_count = 0,
                db_error_count = 0,
                ws_disconnected_minutes = 0,
                today_loss_pct = 0.0,
                mode_changed_at = NOW()
            WHERE id = 1
            """
        )
        self.db.commit()

        print('🔄 시스템 수동 리셋 완료')


# 싱글톤
_safe_mode_manager: Optional[SafeModeManager] = None


def get_safe_mode_manager() -> SafeModeManager:
    global _safe_mode_manager
    if _safe_mode_manager is None:
        _safe_mode_manager = SafeModeManager()
    return _safe_mode_manager
```

### 4.3 AutoTrader 통합

```python
# brain/auto_trader.py (수정)

from brain.micro_opt_logger import get_micro_opt_logger
from utils.safe_mode import get_safe_mode_manager

class AutoTrader:
    def __init__(self):
        self.micro_logger = get_micro_opt_logger()
        self.safe_mode = get_safe_mode_manager()
        # ...

    def execute_buy_order(self, stock_code, amount, ai_score):
        """
        매수 주문 실행 (학습 기반 최적화)
        """
        # 1. SAFE MODE 체크
        if not self.safe_mode.can_place_new_order():
            mode = self.safe_mode.get_current_mode()
            logger.warning(f'🟡 {mode} - 신규 매수 금지')
            return None

        try:
            # 2. 호가 조회
            orderbook = self.kis.get_orderbook(stock_code)
            bid = orderbook['bid1']
            ask = orderbook['ask1']

            # 3. 학습된 최적 전략 조회
            config = self.get_order_config(stock_code)
            spread_bp = int((ask - bid) / bid * 10000)

            # 4. 전략 결정
            if spread_bp < config['maker_spread_min_bp']:
                strategy = 'TAKER'
                wait_seconds = 0
                order_price = ask
            else:
                strategy = 'MAKER'
                wait_seconds = config['maker_wait_seconds']
                order_price = bid

            # 5. 로그 시작
            log_id = self.micro_logger.log_order_attempt(
                stock_code, 'BUY', bid, ask, strategy, wait_seconds
            )

            # 6. 주문 실행
            order_result = self.kis.place_order(
                stock_code=stock_code,
                price=order_price,
                quantity=calculate_qty(amount, order_price),
                order_type='LIMIT' if strategy == 'MAKER' else 'MARKET'
            )

            # 7. 대기 (Maker인 경우)
            if strategy == 'MAKER' and wait_seconds > 0:
                time.sleep(wait_seconds)

                # 체결 확인
                status = self.kis.check_order_status(order_result['order_no'])

                if status['filled_qty'] > 0:
                    # 체결 성공
                    self.micro_logger.log_order_result(
                        log_id,
                        filled=True,
                        filled_price=order_price
                    )
                else:
                    # 미체결 → 정정 (Taker)
                    self.kis.amend_order(order_result['order_no'], ask, 'MARKET')

                    self.micro_logger.log_order_result(log_id, filled=True, filled_price=ask)

            return order_result

        except Exception as e:
            # API 에러 보고
            self.safe_mode.report_api_error(str(e))
            raise

    def get_order_config(self, stock_code: str) -> Dict:
        """종목별 학습된 설정 조회"""
        config = self.db.execute(
            "SELECT * FROM stock_order_config WHERE stock_code = :code",
            {'code': stock_code}
        ).fetchone()

        if config and config['confidence_score'] >= 0.7:
            return dict(config)

        # 기본값
        return {
            'maker_spread_min_bp': 5,
            'maker_wait_seconds': 10,
            'taker_spread_max_bp': 3,
        }
```

---

## 5. 스케줄러 통합

```python
# scheduler/main_scheduler.py (추가)

from brain.micro_opt_logger import get_micro_opt_logger
from utils.safe_mode import get_safe_mode_manager

# 매일 23:00 - 학습 및 최적화
@scheduler.scheduled_job('cron', hour=23, minute=0)
def daily_micro_optimization():
    """일일 미세 최적화 학습"""
    logger = get_micro_opt_logger()

    # 보유 종목 + 자주 거래하는 종목
    stocks = get_frequently_traded_stocks(days=30)

    for stock in stocks:
        logger.analyze_and_optimize(stock['code'])

    print(f'✅ {len(stocks)}개 종목 최적화 학습 완료')

# 매일 06:00 - 에러 카운터 리셋
@scheduler.scheduled_job('cron', hour=6, minute=0)
def reset_error_counters():
    """에러 카운터 초기화"""
    safe_mode = get_safe_mode_manager()

    # 정상 모드면 카운터만 리셋
    if safe_mode.get_current_mode() == 'NORMAL':
        safe_mode.db.execute(
            """
            UPDATE system_mode
            SET api_error_count = 0,
                db_error_count = 0,
                today_loss_pct = 0.0
            WHERE id = 1
            """
        )
        safe_mode.db.commit()

# 매 10분 - 자동 복구 체크
@scheduler.scheduled_job('interval', minutes=10)
def check_auto_recovery():
    """자동 복구 체크"""
    safe_mode = get_safe_mode_manager()
    safe_mode.try_auto_recovery()
```

---

## 6. 예상 효과

### 학습 기반 최적화

```
기존:
  모든 종목 동일 설정 (Maker 10초)
  체결률: 70%
  절약: 0.12% / 건

학습 후:
  종목별 최적화 (삼성전자 5초, 중소형주 15초)
  체결률: 85% (+15%)
  절약: 0.18% / 건 (+0.06%)

연간 효과: +60만원
```

### SAFE MODE

```
시나리오: KIS API 장애 발생

기존:
  계속 매수 시도 → 에러 누적
  잘못된 가격에 체결
  추가 손실: -200만원

SAFE MODE:
  즉시 신규 매수 중단
  보유 포지션만 관리
  손실 최소화: -20만원

차이: 180만원 방어!
```

---

## 7. 다음 단계

### 즉시 구현 (내일)
- [ ] micro_opt_logs 테이블 생성
- [ ] system_mode 테이블 생성
- [ ] SafeModeManager 구현
- [ ] AutoTrader에 SAFE MODE 체크 추가

### 1주일 내
- [ ] MicroOptLogger 구현
- [ ] 학습 기반 최적화 로직
- [ ] 스케줄러 통합

---

**작성일**: 2025-12-08
**작성자**: wonny
**버전**: 1.0.0
**목표**: 연간 +240만원 (학습 60만 + SAFE MODE 180만)
