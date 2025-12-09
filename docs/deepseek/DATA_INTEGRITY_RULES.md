# AEGIS v3.1 데이터 무결성 규칙 문서

## 1. 삭제 금지 정책

### 문제 상황 예시
- 실수로 `DELETE FROM stock_prices WHERE date = '2024-01-15'` 실행 시 과거 모든 주가 데이터 소실
- 분석을 위해 과거 데이터 참조 시 데이터 부재로 인한 보고서 오류 발생
- 규제 준수를 위한 데이터 보존 기간 미충족

### 규칙 설명
**DELETE, TRUNCATE 금지 테이블:**
- 거래 데이터: `stock_transactions`, `option_trades`
- 주가 이력: `stock_prices_history`, `daily_market_data`
- 사용자 활동: `user_activity_logs`, `api_request_logs`
- 시스템 설정: `system_configurations`

**Soft Delete vs Hard Delete 전략:**
- 모든 핵심 비즈니스 테이블은 soft delete 구현 필수
- 로그/임시 데이터만 hard delete 허용
- 삭제 시 `deleted_at` 타임스탬프 및 `deleted_by` 사용자 정보 기록

**히스토리 보존 규칙:**
- 거래 데이터: 7년 보관 (금융 규정 준수)
- 로그 데이터: 2년 보관
- 실시간 데이터: 30일 롤링 보관

### 구현 코드

```python
# Python - Soft Delete 구현 예시
class SoftDeleteMixin:
    def soft_delete(self, user_id: str, reason: str = None):
        """Soft delete 구현"""
        self.deleted_at = datetime.utcnow()
        self.deleted_by = user_id
        self.delete_reason = reason
        self.is_active = False
        self.save()
        
    @classmethod
    def active_objects(cls):
        """삭제되지 않은 객체만 조회"""
        return cls.objects.filter(is_active=True, deleted_at__isnull=True)

# SQL - 히스토리 테이블 생성
CREATE TABLE stock_prices_history (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    price DECIMAL(15, 2) NOT NULL,
    volume BIGINT NOT NULL,
    trade_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    deleted_by VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 히스토리 보존을 위한 인덱스
    INDEX idx_trade_date (trade_date),
    INDEX idx_stock_date (stock_code, trade_date)
) PARTITION BY RANGE (trade_date);
```

### 예외 상황 처리
- **긴급 삭제 필요 시**: DBA 승인 후 `emergency_deletion` 프로시저 실행
- **개인정보 삭제 요청**: GDPR 준수를 위한 별도 `purge_personal_data` 프로시저 사용
- **성능 문제**: 오래된 데이터는 별도 아카이브 테이블로 이동

---

## 2. UPSERT 패턴

### 문제 상황 예시
- 동일 주식에 대한 중복 실시간 데이터 수신 시 충돌 발생
- 배치 작업 중 네트워크 장애로 인한 부분적 업데이트
- 고빈도 업데이트 시 테이블 락 경합

### 규칙 설명
**INSERT ON CONFLICT DO UPDATE 패턴:**
- 실시간 시장 데이터 수집에 필수 적용
- 고유 제약조건(unique constraint) 기반 충돌 해결
- 타임스탬프 기반 최신 데이터 유지

### 구현 코드

```python
# Python - UPSERT 패턴 구현
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

class MarketDataUPSERT:
    def __init__(self, connection):
        self.conn = connection
        self.cursor = self.conn.cursor()
    
    def upsert_stock_prices(self, stock_data_list):
        """
        주식 가격 데이터 UPSERT
        stock_data_list: [(stock_code, price, volume, timestamp), ...]
        """
        upsert_query = """
        INSERT INTO stock_prices (stock_code, price, volume, last_updated, created_at)
        VALUES %s
        ON CONFLICT (stock_code, date(last_updated))
        DO UPDATE SET
            price = EXCLUDED.price,
            volume = EXCLUDED.volume,
            last_updated = EXCLUDED.last_updated,
            updated_count = stock_prices.updated_count + 1
        WHERE EXCLUDED.last_updated > stock_prices.last_updated
        """
        
        try:
            execute_values(self.cursor, upsert_query, stock_data_list)
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"UPSERT 실패: {e}")
            return False
    
    def batch_upsert_optimized(self, data, batch_size=1000):
        """대량 데이터 배치 UPSERT"""
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            self.upsert_stock_prices(batch)
            
            # 커밋 간격으로 인덱스 최적화
            if i % (batch_size * 10) == 0:
                self.cursor.execute("VACUUM ANALYZE stock_prices;")

# SQL - UPSERT 최적화 테이블 구조
CREATE TABLE stock_prices (
    id BIGSERIAL,
    stock_code VARCHAR(10) NOT NULL,
    price DECIMAL(15, 2) NOT NULL,
    volume BIGINT NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_count INTEGER DEFAULT 0,
    
    -- 복합 고유 제약조건
    CONSTRAINT unique_stock_timestamp 
        UNIQUE (stock_code, DATE(last_updated)),
    
    -- 성능을 위한 인덱스
    INDEX idx_stock_last_updated (stock_code, last_updated DESC)
) WITH (fillfactor=90);
```

### 성능 최적화 팁
1. **배치 처리**: 1000-5000건 단위로 UPSERT 실행
2. **인덱스 최적화**: 부분적 인덱스(partial index) 사용
   ```sql
   CREATE INDEX idx_recent_prices ON stock_prices (stock_code)
   WHERE last_updated > CURRENT_DATE - INTERVAL '30 days';
   ```
3. **커넥션 풀링**: 지속적 연결 재사용
4. **비동기 처리**: 고빈도 데이터는 Kafka → PostgreSQL 파이프라인 구성

### 예외 상황 처리
- **데이터 충돌**: `last_updated` 기준 최신 데이터 유지
- **네트워크 장애**: 재시도 로직 + 장애 데이터 큐잉
- **스키마 변경**: zero-downtime 마이그레이션 적용

---

## 3. Single Source of Truth

### 문제 상황 예시
- KIS API 데이터와 로컬 캐시 간 불일치
- 여러 시스템에서 동일 데이터를 다른 값으로 참조
- 실시간 데이터와 배치 데이터 간 차이

### 규칙 설명
**데이터 원본 정의:**
1. **실시간 시세**: KIS API Websocket (1차 원본)
2. **기업 기본정보**: 한국거래소 공시시스템 (2차 원본)
3. **거래 데이터**: 증권사 체결 시스템 (3차 원본)

**KIS API vs DB 캐시 역할:**
- KIS API: 실시간 데이터 원천 (Read-Only)
- DB 캐시: 가공/집계 데이터 저장 (Read-Write)
- 캐시 무효화: TTL(Time-To-Live) 5초 적용

### 구현 코드

```python
# Python - Single Source of Truth 관리
import redis
from typing import Optional, Dict
from datetime import datetime, timedelta

class DataSourceManager:
    def __init__(self):
        self.redis_client = redis.Redis(host='redis', port=6379, db=0)
        self.cache_ttl = 5  # 초 단위
        
    async def get_stock_price(self, stock_code: str) -> Optional[Dict]:
        """
        데이터 흐름: API → 캐시 → DB
        1. 캐시 체크 (가장 빠름)
        2. 캐시 미스 시 API 호출
        3. 결과 캐시 및 DB 저장
        """
        cache_key = f"stock:{stock_code}:price"
        
        # 1. 캐시에서 조회
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
        
        # 2. KIS API 호출 (실시간 데이터)
        try:
            api_data = await self._call_kis_api(stock_code)
            
            # 3. 캐시 저장
            self.redis_client.setex(
                cache_key, 
                self.cache_ttl, 
                json.dumps(api_data)
            )
            
            # 4. DB 저장 (UPSERT)
            await self._save_to_database(api_data)
            
            return api_data
            
        except Exception as e:
            # 5. 실패 시 DB에서 최신 데이터 조회
            logger.warning(f"API 실패, DB 폴백: {e}")
            return await self._get_from_database(stock_code)
    
    def _call_kis_api(self, stock_code: str):
        """KIS API 호출 (실제 구현)"""
        # API 호출 로직
        pass
    
    async def _save_to_database(self, data: Dict):
        """DB 저장 with UPSERT"""
        query = """
        INSERT INTO stock_prices_truth 
        (stock_code, price, volume, source, received_at)
        VALUES (%s, %s, %s, 'KIS_API', %s)
        ON CONFLICT (stock_code, received_at)
        DO UPDATE SET 
            price = EXCLUDED.price,
            volume = EXCLUDED.volume
        """
        # 실행 로직
```

### 동기화 전략
1. **실시간 동기화**: WebSocket + Change Data Capture
   ```python
   # CDC 구현 예시
   async def cdc_listener():
       async for change in listen_to_wal():
           if change.table == 'stock_prices':
               await publish_to_cache(change)
   ```

2. **배치 동기화**: 매일 00:00 전체 데이터 무결성 검사
   ```sql
   -- 일일 데이터 무결성 체크
   CREATE PROCEDURE daily_integrity_check()
   AS $$
   BEGIN
       -- API 데이터 vs DB 데이터 비교
       WITH api_data AS (
           SELECT stock_code, MAX(price) as api_price
           FROM external_api_sync
           WHERE date = CURRENT_DATE
           GROUP BY stock_code
       ),
       db_data AS (
           SELECT stock_code, MAX(price) as db_price
           FROM stock_prices
           WHERE DATE(last_updated) = CURRENT_DATE
           GROUP BY stock_code
       )
       SELECT 
           a.stock_code,
           ABS(a.api_price - d.db_price) as price_diff,
           CASE 
               WHEN ABS(a.api_price - d.db_price) > 0.1 
               THEN 'INCONSISTENT'
               ELSE 'OK'
           END as status
       FROM api_data a
       JOIN db_data d ON a.stock_code = d.stock_code;
   END;
   $$ LANGUAGE plpgsql;
   ```

3. **충돌 해결**: 타임스탬프 + 버전 관리
   ```sql
   ALTER TABLE stock_prices_truth 
   ADD COLUMN data_version INTEGER DEFAULT 1,
   ADD COLUMN checksum VARCHAR(64);
   ```

### 예외 상황 처리
- **API 장애**: 캐시 데이터로 서비스 지속 (데그레이드 모드)
- **데이터 불일치**: 수동 조정 프로세스 실행
- **네트워크 지연**: 비동기 큐에 작업 저장

---

## 4. 데이터 검증

### 문제 상황 예시
- 주가가 전일 대비 150% 상승한 이상 데이터 수신
- 거래량이 평균의 1000배인 이상치 발생
- 휴장일인데 거래 데이터 수신

### 규칙 설명
**수익률 ±50% 이상 경고:**
- 전일 종가 대비 ±50% 이상 변동 시 실시간 알림
- 20분 봉 기준 이상치 감지

**거래량 이상 탐지:**
- 30일 평균 거래량 대비 500% 이상 시 검증
- 시가총액 대비 비정상적 거래량 감지

**가격 갭 검증:**
- 전일 종가와 당일 시가 간 ±20% 이상 갭 검증
- 무상/유상 증자 등 corporate action 반영

### 구현 코드

```python
# Python - 데이터 검증 클래스
import numpy as np
from scipy import stats
from typing import Tuple, Optional

class DataValidator:
    def __init__(self):
        self.anomaly_thresholds = {
            'price_change': 0.50,  # 50%
            'volume_spike': 5.00,   # 500%
            'price_gap': 0.20,      # 20%
        }
    
    def validate_price_change(self, 
                             current_price: float, 
                             previous_close: float) -> Tuple[bool, str]:
        """
        수익률 ±50% 이상 경고 검증
        """
        if previous_close == 0:
            return False, "이전 종가가 0입니다"
        
        change_pct = abs((current_price - previous_close) / previous_close)
        
        if change_pct > self.anomaly_thresholds['price_change']:
            alert_msg = (
                f"주가 급등락 경고: {change_pct:.1%} 변동\n"
                f"전일종가: {previous_close:,}\n"
                f"현재가: {current_price:,}"
            )
            return True, alert_msg
        
        return False, "정상 범위"
    
    def detect_volume_anomaly(self, 
                             current_volume: int, 
                             historical_volumes: list) -> Tuple[bool, dict]:
        """
        거래량 이상 탐지 (Z-score 기반)
        """
        if len(historical_volumes) < 5:
            return False, {"reason": "데이터 부족"}
        
        volumes = np.array(historical_volumes)
        
        # Z-score 계산
        z_score = (current_volume - volumes.mean()) / volumes.std()
        
        # IQR(사분위간 범위) 방법
        Q1 = np.percentile(volumes, 25)
        Q3 = np.percentile(volumes, 75)
        IQR = Q3 - Q1
        upper_bound = Q3 + 1.5 * IQR
        
        metrics = {
            'z_score': float(z_score),
            'current_vs_avg': current_volume / volumes.mean(),
            'is_iqr_outlier': current_volume > upper_bound
        }
        
        is_anomaly = (
            abs(z_score) > 3 or 
            metrics['current_vs_avg'] > self.anomaly_thresholds['volume_spike']
        )
        
        return is_anomaly, metrics
    
    def validate_price_gap(self, 
                          open_price: float, 
                          previous_close: float) -> Tuple[bool, float]:
        """
        가격 갭 검증
        """
        if previous_close == 0:
            return False, 0.0
        
        gap_pct = abs((open_price - previous_close) / previous_close)
        is_anomalous = gap_pct > self.anomaly_thresholds['price_gap']
        
        return is_anomalous, gap_pct
    
    def comprehensive_validation(self, 
                                stock_data: dict) -> dict:
        """
        종합 검증 실행
        """
        results = {
            'timestamp': datetime.utcnow(),
            'stock_code': stock_data['code'],
            'validations': {},
            'alerts': [],
            'overall_status': 'PASS'
        }
        
        # 1. 가격 변동 검증
        price_valid, price_msg = self.validate_price_change(
            stock_data['price'],
            stock_data['previous_close']
        )
        results['validations']['price_change'] = {
            'is_anomaly': price_valid,
            'message': price_msg
        }
        if price_valid:
            results['alerts'].append(price_msg)
            results['overall_status'] = 'WARNING'
        
        # 2. 거래량 이상 탐지
        volume_valid, volume_metrics = self.detect_volume_anomaly(
            stock_data['volume'],
            stock_data['volume_history']
        )
        results['validations']['volume'] = {
            'is_anomaly': volume_valid,
            'metrics': volume_metrics
        }
        if volume_valid:
            results['alerts'].append(f"거래량 이상: {volume_metrics}")
            results['overall_status'] = 'WARNING'
        
        # 3. 가격 갭 검증
        gap_valid, gap_pct = self.validate_price_gap(
            stock_data['open'],
            stock_data['previous_close']
        )
        results['validations']['price_gap'] = {
            'is_anomaly': gap_valid,
            'gap_percentage': gap_pct
        }
        
        return results
```

### SQL 검증 쿼리

```sql
-- 일일 데이터 품질 검증 리포트
CREATE OR REPLACE VIEW data_quality_daily_report AS
SELECT 
    date,
    stock_code,
    -- 가격 검증
    CASE 
        WHEN ABS((close_price - prev_close) / prev_close) > 0.5 
        THEN 'PRICE_ANOMALY'
        ELSE 'NORMAL'
    END as price_status,
    
    -- 거래량 검증
    CASE 
        WHEN volume > AVG(volume) OVER (
            PARTITION BY stock_code 
            ORDER BY date 
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) * 5
        THEN 'VOLUME_SPIKE'
        ELSE 'NORMAL'
    END as volume_status,
    
    -- 갭 검증
    CASE 
        WHEN ABS((open_price - prev_close) / prev_close) > 0.2
        THEN 'PRICE_GAP'
        ELSE 'NORMAL'
    END as gap_status,
    
    -- 종합 상태
    CASE 
        WHEN price_status = 'PRICE_ANOMALY' 
            OR volume_status = 'VOLUME_SPIKE'
            OR gap_status = 'PRICE_GAP'
        THEN 'REQUIRES_REVIEW'
        ELSE 'VALIDATED'
    END as overall_status
    
FROM stock_prices_daily
WHERE date >= CURRENT_DATE - INTERVAL '7 days';
```

### 예외 상황 처리
1. **이상 데이터 식별 시**:
   - 즉시 트레이딩 중단 (circuit breaker)
   - 관리자 알림 발송
   - 검증 큐로 이동

2. **거래량 폭주 시**:
   - 별도 로깅 시스템으로 분리
   - 샘플링된 데이터만 실시간 처리

3. **시스템 부하 시**:
   - 검증 규칙 우선순위 조정
   - 비핵심 검증 일시 중단

---

## 5. 복구 절차

### 문제 상황 예시
- 잘못된 배치 작업으로 1시간 분량 데이터 손실
- KIS API 장애로 인한 데이터 동기화 누락
- 하드웨어 장애로 인한 데이터베이스 손상

### 규칙 설명
**데이터 손상 시 복구:**
1. **손상 평가**: 영향 범위 및 심각도 평가
2. **복구 전략**: Point-in-Time vs 전체 복구 결정
3. **검증**: 복구 후 데이터 무결성 검증

**KIS API 재동기화:**
- 증분 동기화 vs 전체 재동기화
- 타임스탬프 기반 재처리

**백업 데이터 활용:**
- 멀티 리전 백업 (서울, 도쿄, 싱가포르)
- 3-2-1 백업 전략 (3개 복사본, 2개 미디어, 1개 오프사이트)

### 구현 코드

```python
# Python - 데이터 복구 관리자
import boto3
from datetime import datetime, timedelta
import pg8000
from typing import List

class DataRecoveryManager:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.backup_bucket = 'aegis-backups'
        self.wal_bucket = 'aegis-wal-backups'
        
    def assess_data_corruption(self, 
                              table_name: str, 
                              start_time: datetime,
                              end_time: datetime) -> dict:
        """
        데이터 손상 평가
        """
        assessment = {
            'table': table_name,
            'time_range': {
                'start': start_time,
                'end': end_time
            },
            'affected_rows': 0,
            'severity': 'UNKNOWN',
            'recovery_strategy': None
        }
        
        # 손상된 행 수 확인
        query = f"""
        SELECT COUNT(*) as corrupted_count
        FROM {table_name}
        WHERE last_updated BETWEEN %s AND %s
        AND (price <= 0 OR volume < 0 OR price IS NULL)
        """
        
        # 실행 결과 분석
        # ...
        
        # 심각도 평가
        if assessment['affected_rows'] > 10000:
            assessment['severity'] = 'CRITICAL'
            assessment['recovery_strategy'] = 'FULL_RESTORE'
        elif assessment['affected_rows'] > 1000:
            assessment['severity'] = 'HIGH'
            assessment['recovery_strategy'] = 'POINT_IN_TIME'
        else:
            assessment['severity'] = 'LOW'
            assessment['recovery_strategy'] = 'INCREMENTAL'
            
        return assessment
    
    def restore_from_backup(self, 
                           table_name: str, 
                           restore_time: datetime,
                           strategy: str = 'POINT_IN_TIME') -> bool:
        """
        백업에서 데이터 복구
        """
        try:
            if strategy == 'POINT_IN_TIME':
                return self._point_in_time_restore(table_name, restore_time)
            elif strategy == 'INCREMENTAL':
                return self._incremental_restore(table_name, restore_time)
            else:
                return self._full_restore(table_name)
                
        except Exception as e:
            logger.error(f"복구 실패: {e}")
            return False
    
    def _point_in_time_restore(self, table_name: str, target_time: datetime):
        """
        지정 시간 복구
        """
        # 1. 가장 가까운 전체 백업 찾기
        base_backup = self._find_base_backup(table_name, target_time)
        
        # 2. WAL(Write-Ahead Log) 적용
        wal_files = self._get_wal_files(base_backup['timestamp'], target_time)
        
        # 3. 복구 실행
        recovery_commands = [
            f"CREATE TEMP TABLE {table_name}_recovery AS SELECT * FROM {table_name} WHERE 1=0;",
            f"COPY {table_name}_recovery FROM '{base_backup['s3_path']}';",
            # WAL 적용
            *[f"APPLY WAL '{wal_file}' TO {table_name}_recovery;" 
              for wal_file in wal_files],
            # 손상된 데이터 교체
            f"""
            WITH recovered AS (
                SELECT * FROM {table_name}_recovery
                WHERE last_updated <= %s
            )
            INSERT INTO {table_name}
            SELECT * FROM recovered
            ON CONFLICT (id)
            DO UPDATE SET
                price = EXCLUDED.price,
                volume = EXCLUDED.volume,
                last_updated = EXCLUDED.last_updated,
                recovery_flag = TRUE
            """,
        ]
        
        # 명령어 실행
        return self._execute_recovery(recovery_commands, target_time)
    
    def resync_kis_api(self, 
                      stock_codes: List[str], 
                      start_date: datetime,
                      end_date: datetime) -> dict:
        """
        KIS API 재동기화
        """
        results = {
            'total_stocks': len(stock_codes),
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        for stock_code in stock_codes:
            try:
                # 증분 데이터 가져오기
                api_data = self._fetch_kis_data(
                    stock_code, 
                    start_date, 
                    end_date
                )
                
                # UPSERT 실행
                self._bulk_upsert(api_data)
                
                results['successful'] += 1
                results['details'].append({
                    'stock_code': stock_code,
                    'status': 'SUCCESS',
                    'records': len(api_data)
                })
                
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'stock_code': stock_code,
                    'status': 'FAILED',
                    'error': str(e)
                })
                
        return results

# SQL - 복구 프로시저
CREATE OR REPLACE PROCEDURE emergency_data_recovery(
    p_table_name VARCHAR,
    p_corruption_start TIMESTAMP,
    p_corruption_end TIMESTAMP
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_backup_path TEXT;
    v_wal_files TEXT[];
    v_row_count INTEGER;
BEGIN
    -- 1. 손상된 데이터 백업 (분석용)
    EXECUTE format('
        CREATE TABLE %I_corrupted_backup AS 
        SELECT * FROM %I 
        WHERE last_updated BETWEEN $1 AND $2',
        p_table_name, p_table_name)
    USING p_corruption_start, p_corruption_end;
    
    -- 2. 백업 파일 찾기
    SELECT backup_location INTO v_backup_path
    FROM backup_metadata
    WHERE table_name = p_table_name
      AND backup_time <= p_corruption_start
    ORDER BY backup_time DESC
    LIMIT 1;
    
    -- 3. WAL 파일 목록 가져오기
    SELECT ARRAY_AGG(wal_file)
    INTO v_wal_files
    FROM wal_logs
    WHERE table_name = p_table_name
      AND log_time BETWEEN p_corruption_start AND p_corruption_end;
    
    -- 4. 복구 실행
    PERFORM restore_table_from_backup(
        p_table_name,
        v_backup_path,
        v_wal_files,
        p_corruption_end
    );
    
    -- 5. 검증
    EXECUTE format('
        SELECT COUNT(*) FROM %I 
        WHERE last_updated BETWEEN $1 AND $2
        AND recovery_flag = TRUE',
        p_table_name)
    INTO v_row_count
    USING p_corruption_start, p_corruption_end;
    
    -- 6. 로깅
    INSERT INTO recovery_logs (
        table_name,
        recovery_time,
        recovered_rows,
        backup_used,
        status
    ) VALUES (
        p_table_name,
        CURRENT_TIMESTAMP,
        v_row_count,
        v_backup_path,
        'COMPLETED'
    );
    
    COMMIT;
    
    RAISE NOTICE '복구 완료: % 행 복원', v_row_count;
    
EXCEPTION WHEN OTHERS THEN
    ROLLBACK;
    RAISE EXCEPTION '복구 실패: %', SQLERRM;
END;
$$;
```

### 백업 전략

```yaml
# backup_policy.yaml
backup_strategy:
  full_backup:
    schedule: "0 2 * * *"  # 매일 오전 2시
    retention: 30일
    compression: zstd
    
  incremental_backup:
    schedule: "*/15 * * * *"  # 15분마다
    retention: 7일
    
  wal_archiving:
    enabled: true
    continuous: true
    retention: 14일
    
  geographic_redundancy:
    regions:
      - ap-northeast-2  # 서울
      - ap-northeast-1  # 도쿄
      - ap-southeast-1  # 싱가포르
    replication: async
    
recovery_objectives:
  rto: "4시간"  # Recovery Time Objective
  rpo: "15분"   # Recovery Point Objective
  mtta: "30분"  # Mean Time To Acknowledge
  mttr: "2시간" # Mean Time To Recover
```

### 예외 상황 처리

1. **부분적 손상**:
   ```python
   # 단계적 복구
   def staged_recovery(self, table_name, time_ranges):
       for start, end in time_ranges:
           if not self.restore_from_backup(table_name, start, end):
               logger.error(f"{start}-{end} 구간 복구 실패")
               # 다음 구간으로 계속
               continue
   ```

2. **백업 손상**:
   - 2차 백업 위치에서 복구 시도
   - KIS API로부터 재수집 (마지막 수단)

3. **복구 중 서비스**:
   - 읽기 전용 모드로 전환
   - 캐시 레이어로 임시 서비스
   - 사용자에게 진행 상황 공지

4. **검증 실패**:
   ```sql
   -- 복구 후 무결성 검증
   SELECT 
       table_name,
       COUNT(*) as total_rows,
       SUM(CASE WHEN recovery_flag THEN 1 ELSE 0 END) as recovered_rows,
       SUM(CASE WHEN price <= 0 OR volume < 0 THEN 1 ELSE 0 END) as invalid_rows
   FROM recovered_tables
   GROUP BY table_name
   HAVING SUM(CASE WHEN price <= 0 OR volume < 0 THEN 1 ELSE 0 END) > 0;
   ```

---

## 요약

AEGIS v3.1 데이터 무결성 프레임워크는 다음 원칙을 기반으로 합니다:

1. **예방**: 삭제 금지, UPSERT 패턴, 검증 규칙으로 문제 예방
2. **일관성**: Single Source of Truth로 데이터 불일치 방지
3. **복구**: 체계적 백업 및 복구 절차로 가용성 보장
4. **모니터링**: 실시간 검증 및 알림으로 조기 대응

이 문서에 명시된 규칙과 절차는 AEGIS 시스템의 데이터 품질과 신뢰성을 보장하기 위해 필수적으로 준수되어야 합니다. 모든 변경사항은 변경 관리 절차를 통해 문서화되고, 정기적인 감사를 통해 준수 여부를 확인해야 합니다.
