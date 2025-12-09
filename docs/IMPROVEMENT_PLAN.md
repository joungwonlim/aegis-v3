# AEGIS v3.0 개선 계획

> **분석 일자**: 2025-12-09
> **분석 도구**: DeepSeek R1 (Reasoner Model)
> **분석 대상**: dev3 문서 전체 (README, CORE_PHILOSOPHY, DATABASE_DESIGN, PYRAMIDING_STRATEGY)

---

## 📋 목차

1. [분석 개요](#분석-개요)
2. [즉시 적용 가능한 개선사항](#즉시-적용-가능한-개선사항)
3. [중기 개선사항](#중기-개선사항)
4. [보류/불필요 사항](#보류불필요-사항)
5. [실행 우선순위](#실행-우선순위)

---

## 📊 분석 개요

DeepSeek R1 모델을 통해 AEGIS v3.0 시스템을 다음 4가지 관점에서 분석했습니다:

1. **전체 시스템 구조 분석**
2. **데이터베이스 설계 리뷰**
3. **피라미딩 전략 검증**
4. **개선 기회 발굴**

### 분석 결과 요약

- ✅ **강점**: 3-Layer AI 시스템, 체계적인 DB 설계, 피라미딩 전략
- ⚠️ **개선 필요**: AI 비용 최적화, 모니터링 강화, 손절 전략 정교화
- 🚫 **과도한 제안**: 마이크로서비스, 이벤트 기반 아키텍처 (현재 불필요)

---

## 🎯 즉시 적용 가능한 개선사항

### 1. AI 비용 최적화 (캐싱 레이어)

**문제점**:
- 3-Layer AI (Flash → Pro → Opus) 시스템의 API 호출 비용이 높음
- 동일한 조건에 대한 중복 분석 발생 가능

**해결 방안**:
```python
# brain/ai_cache.py (신규 생성)
from functools import lru_cache
from datetime import datetime, timedelta
import hashlib
import json

class AIResponseCache:
    """AI 응답 캐싱 시스템"""

    def __init__(self, ttl_minutes=60):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def get_cache_key(self, stock_code, analysis_type, params):
        """캐시 키 생성"""
        data = {
            'stock_code': stock_code,
            'analysis_type': analysis_type,
            'params': params
        }
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def get(self, key):
        """캐시 조회"""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry['timestamp'] < self.ttl:
                return entry['data']
            else:
                del self.cache[key]
        return None

    def set(self, key, data):
        """캐시 저장"""
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now()
        }
```

**적용 위치**:
- `brain/analyzer.py` → AI 분석 함수에 캐싱 추가
- `brain/auto_trader.py` → 종목 선정 시 캐시 우선 확인

**기대 효과**:
- API 호출 비용 **30-50% 절감**
- 응답 속도 향상 (캐시 히트 시 즉시 반환)

---

### 2. Grafana 모니터링 시스템

**문제점**:
- 현재 시스템 상태를 실시간으로 확인하기 어려움
- Telegram 알림만으로는 전체적인 건강 상태 파악 제한적

**해결 방안**:
```yaml
# docker-compose.yml에 Grafana 추가
services:
  grafana:
    image: grafana/grafana:latest
    container_name: aegis-v2-grafana
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=aegis2024
      - GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./config/grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - db
    networks:
      - aegis-network
    restart: unless-stopped

volumes:
  grafana_data:
    name: aegis-v2-grafana
```

**모니터링 대시보드**:
1. **AI 성능 모니터링**
   - AI 정확도 (daily_picks vs 실제 수익)
   - 모델별 호출 횟수 및 비용
   - 응답 시간

2. **매매 성과**
   - 일일/주간/월간 수익률
   - 승률 추이
   - 손익 분포

3. **시스템 건강**
   - Fetcher 성공률
   - API 호출 실패율
   - DB 쿼리 성능

**적용 위치**:
- `docker-compose.yml` → Grafana 서비스 추가
- `config/grafana/` → 대시보드 설정 파일
- `database/models.py` → 모니터링용 뷰 추가

**기대 효과**:
- 시스템 문제 **조기 발견**
- 데이터 기반 의사결정
- 성과 시각화로 전략 개선

---

### 3. 변동성 기반 손절선 (Volatility-based Stop Loss)

**문제점**:
- 현재 모든 종목에 동일한 -2% 손절선 적용
- 백테스트 결과 Wide Stop (-7%)이 더 나은 성과 (Tight Stop -2%는 -15.54% 손실)
- 종목별 변동성 차이 미반영

**해결 방안**:
```python
# brain/risk_manager.py (신규 생성)
import numpy as np
from database.models import DailyPrice

class VolatilityStopLoss:
    """변동성 기반 손절선 계산"""

    def calculate_atr_stop(self, stock_code, atr_multiplier=2.0, lookback=14):
        """
        ATR(Average True Range) 기반 손절선

        Args:
            stock_code: 종목 코드
            atr_multiplier: ATR 배수 (기본 2배)
            lookback: ATR 계산 기간 (기본 14일)

        Returns:
            stop_loss_percentage: 손절 비율 (예: -3.5%)
        """
        # 최근 14일 가격 데이터 조회
        prices = DailyPrice.query.filter_by(stock_code=stock_code)\
            .order_by(DailyPrice.date.desc())\
            .limit(lookback + 1)\
            .all()

        if len(prices) < lookback:
            return -2.0  # 데이터 부족 시 기본값

        # True Range 계산
        true_ranges = []
        for i in range(1, len(prices)):
            high = prices[i].high_price
            low = prices[i].low_price
            prev_close = prices[i-1].close_price

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)

        # ATR 계산
        atr = np.mean(true_ranges)
        current_price = prices[0].close_price

        # 손절 비율 = (ATR * 배수) / 현재가
        stop_loss_pct = -(atr * atr_multiplier / current_price) * 100

        # 최소 -1%, 최대 -10% 제한
        return max(min(stop_loss_pct, -1.0), -10.0)

    def calculate_std_stop(self, stock_code, std_multiplier=2.0, lookback=20):
        """
        표준편차 기반 손절선

        Returns:
            stop_loss_percentage: 손절 비율
        """
        prices = DailyPrice.query.filter_by(stock_code=stock_code)\
            .order_by(DailyPrice.date.desc())\
            .limit(lookback)\
            .all()

        if len(prices) < lookback:
            return -2.0

        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i-1].close_price - prices[i].close_price) / prices[i].close_price
            returns.append(ret)

        std = np.std(returns)
        stop_loss_pct = -(std * std_multiplier) * 100

        return max(min(stop_loss_pct, -1.0), -10.0)
```

**적용 전략**:
```python
# 종목별 변동성에 따른 손절선 차등 적용
삼성전자 (변동성 낮음): -2% ~ -3%
테슬라 (변동성 높음): -5% ~ -7%
중소형주 (변동성 매우 높음): -7% ~ -10%
```

**적용 위치**:
- `brain/risk_manager.py` → 신규 생성
- `brain/auto_trader.py` → 매매 시 동적 손절선 적용
- `database/models.py` → Portfolio 테이블에 `dynamic_stop_loss` 컬럼 추가

**기대 효과**:
- 백테스트 수익률 **+4.90% → +7~8%** 개선 예상
- 종목 특성에 맞는 리스크 관리
- 불필요한 손절 감소 (변동성 높은 종목)

---

### 4. 백테스트 시스템 강화

**문제점**:
- 현재 단순 백테스트만 존재
- 과최적화(Overfitting) 위험
- 실전 성과와 괴리 가능

**해결 방안**:
```python
# backtester/walk_forward.py (신규 생성)
from datetime import datetime, timedelta
from backtester.engine_v2 import BacktestEngine

class WalkForwardOptimizer:
    """Walk-Forward Optimization 구현"""

    def __init__(self, train_period=60, test_period=20):
        """
        Args:
            train_period: 학습 기간 (일)
            test_period: 검증 기간 (일)
        """
        self.train_period = train_period
        self.test_period = test_period

    def optimize(self, start_date, end_date, strategy_params):
        """
        Walk-Forward 최적화 실행

        프로세스:
        1. 60일 데이터로 학습 → 최적 파라미터 발견
        2. 다음 20일로 검증 → 실전 성과 측정
        3. 윈도우를 20일 이동 → 반복
        """
        results = []
        current_date = start_date

        while current_date + timedelta(days=self.train_period + self.test_period) <= end_date:
            # 학습 구간
            train_start = current_date
            train_end = current_date + timedelta(days=self.train_period)

            # 검증 구간
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_period)

            # 학습: 최적 파라미터 탐색
            best_params = self._find_best_params(
                train_start, train_end, strategy_params
            )

            # 검증: 실전 성과 측정
            test_result = self._run_backtest(
                test_start, test_end, best_params
            )

            results.append({
                'train_period': (train_start, train_end),
                'test_period': (test_start, test_end),
                'params': best_params,
                'test_performance': test_result
            })

            # 윈도우 이동
            current_date += timedelta(days=self.test_period)

        return self._aggregate_results(results)
```

**적용 위치**:
- `backtester/walk_forward.py` → 신규 생성
- `scripts/optimize_strategy.py` → Walk-Forward 통합

**기대 효과**:
- 과최적화 방지
- 실전 성과와 백테스트 괴리 감소
- 시장 변화에 적응하는 전략

---

## 📅 중기 개선사항

### 5. 실시간 웹소켓 시세

**현재**: 30초 배치 갱신
**개선**: 웹소켓을 통한 실시간 시세 (KIS API WebSocket)

**적용 시기**: Q1 2025

---

### 6. 멀티 계좌 지원

**현재**: 단일 계좌
**개선**: 여러 계좌 동시 운영 (가족 계좌 등)

**적용 시기**: 계좌가 3개 이상 늘어날 때

---

## 🚫 보류/불필요 사항

### 7. 마이크로서비스 전환 (불필요)
- **이유**: 현재 모놀리식 구조로 충분, 오버엔지니어링
- **결정**: 보류

### 8. Kafka/RabbitMQ (불필요)
- **이유**: 실시간 이벤트 처리 필요성 낮음
- **결정**: 보류

### 9. Kubernetes (불필요)
- **이유**: Docker Compose로 충분
- **결정**: 보류

### 10. 데이터베이스 분리 (불필요)
- **이유**: 6개 스키마는 논리적 구분일 뿐, 복잡도 적절
- **결정**: 현재 구조 유지

---

## 🎯 실행 우선순위

### Phase 1: 즉시 (1-2주)
1. ✅ **AI 캐싱 레이어** - 비용 절감 효과 즉시 체감
2. ✅ **변동성 기반 손절** - 백테스트 성과 개선

### Phase 2: 단기 (1개월)
3. ✅ **Grafana 모니터링** - 시스템 가시성 확보
4. ✅ **Walk-Forward 백테스트** - 전략 검증 강화

### Phase 3: 중기 (3개월)
5. ⏳ 실시간 웹소켓
6. ⏳ 멀티 계좌 지원

---

## 📈 예상 효과

| 개선사항 | 예상 효과 | 측정 지표 |
|---------|----------|----------|
| AI 캐싱 | API 비용 -40% | 월 API 호출 횟수 |
| 변동성 손절 | 수익률 +3~5%p | 백테스트 연간 수익률 |
| Grafana | 문제 조기 발견 | MTTR (평균 복구 시간) |
| Walk-Forward | 실전 괴리 -50% | 백테스트 vs 실전 수익률 차이 |

---

## 📝 참고 문서

- [CORE_PHILOSOPHY.md](./CORE_PHILOSOPHY.md) - 시스템 설계 철학
- [DATABASE_DESIGN.md](./DATABASE_DESIGN.md) - DB 스키마
- [PYRAMIDING_STRATEGY.md](./PYRAMIDING_STRATEGY.md) - 피라미딩 전략
- [BACKEND_MICRO_OPT.md](./BACKEND_MICRO_OPT.md) - 미세 최적화

---

**작성**: 2025-12-09 13:05
**분석 모델**: DeepSeek R1 (Reasoner)
**검토자**: Claude Sonnet 4.5
