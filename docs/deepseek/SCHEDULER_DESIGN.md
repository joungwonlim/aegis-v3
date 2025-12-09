# AEGIS Scheduler v3.1 - 개선된 작업 스케줄링 시스템 설계 문서

## 1. 개요
AEGIS Scheduler는 금융 트레이딩 환경을 위한 자동화된 작업 스케줄링 시스템입니다. 본 문서는 v3.1에서 도입된 개선사항을 중점적으로 설명합니다.

## 2. 시스템 아키텍처

### 2.1. 핵심 컴포넌트
- **스케줄러 엔진**: 작업 실행을 관리하는 핵심 엔진
- **작업 큐**: 실행 대기 작업을 관리하는 우선순위 큐
- **의존성 관리자**: 작업 간 선후 관계를 관리
- **실패 복구 핸들러**: 작업 실패 시 재시도 및 복구 절차 실행
- **리소스 관리자**: 동시 실행 작업 수 제어
- **휴일 캘린더**: 공휴일 및 휴장일 정보 관리

## 3. 개선된 스케줄링 정책

### 3.1. 정밀한 크론 표현식
| 작업 유형 | 크론 표현식 | 실행 시간 | 설명 |
|-----------|-------------|-----------|------|
| **장 시작 전** | `0 8 * * 1-5` | 08:00 | 평일 08:00 데이터 수집 시작 |
| 데이터 수집 | `*/15 8 * * 1-5` | 08:00-08:45 | 15분 간격 데이터 수집 |
| AI 분석 | `30 8 * * 1-5` | 08:30 | 수집 데이터 기반 AI 분석 |
| **장 중** | `0 9 * * 1-5` | 09:00 | 시장 오픈 |
| 실시간 모니터링 | `* 9-15 * * 1-5` | 09:00-15:30 | 초단위 모니터링 |
| 매매 실행 | `*/5 9-15 * * 1-5` | 09:00-15:30 | 5분 간격 매매 로직 실행 |
| **장 마감 후** | `30 15 * * 1-5` | 15:30 | 정산 작업 시작 |
| 일일 리포트 | `0 16 * * 1-5` | 16:00 | 리포트 생성 |
| **야간 작업** | `0 0 * * *` | 00:00 | 일일 백테스트 시작 |
| 시스템 점검 | `0 2 * * *` | 02:00 | 시스템 점검 실행 |

### 3.2. 의존성 관리 시스템
```yaml
작업 의존성 그래프:
  morning_data_collection:
    depends_on: []
    triggers: [ai_analysis]
    
  ai_analysis:
    depends_on: [morning_data_collection]
    triggers: [market_monitoring]
    
  market_monitoring:
    depends_on: [ai_analysis]
    triggers: [trading_execution]
    
  daily_settlement:
    depends_on: [market_monitoring]
    triggers: [daily_report]
    
  daily_report:
    depends_on: [daily_settlement]
    triggers: []


### 3.3. 실패 복구 정책
```yaml
재시도 정책:
  max_retries: 3
  retry_delay: "exponential"  # 지수적 백오프
  initial_delay: 60초
  max_delay: 300초
  
실패 알림:
  channels:
    - email: "alert@aegis-trading.com"
    - slack: "#system-alerts"
    - sms: "+821012345678"
  
알림 조건:
  - 즉시 알림: 첫 번째 실패
  - 추가 알림: 모든 재시도 실패 시
  - 긴급 알림: 핵심 작업 실패 시


### 3.4. 리소스 관리
```yaml
리소스 제한:
  max_concurrent_jobs: 10
  resource_groups:
    data_processing: 4
    ai_analysis: 3
    trading: 2
    reporting: 1
    
우선순위 시스템:
  level_0: 긴급 (시스템 장애)
  level_1: 높음 (매매 실행)
  level_2: 중간 (데이터 처리)
  level_3: 낮음 (리포트 생성)


### 3.5. 휴일 처리 로직
```python
class HolidayHandler:
    def __init__(self):
        self.holiday_calendar = {
            'fixed': [
                '01-01',  # 신정
                '03-01',  # 삼일절
                '05-05',  # 어린이날
                '06-06',  # 현충일
                '08-15',  # 광복절
                '10-03',  # 개천절
                '10-09',  # 한글날
                '12-25'   # 크리스마스
            ],
            'lunar': [
                '설날',
                '추석'
            ],
            'market_closed': [
                '토요일',
                '일요일'
            ]
        }
    
    def should_skip_job(self, date):
        # 공휴일 확인
        if date in self.holiday_calendar['fixed']:
            return True
        # 주말 확인
        if date.weekday() >= 5:  # 토, 일
            return True
        # 휴장일 확인 (거래소 공식 휴장일)
        if self.is_market_holiday(date):
            return True
        return False


## 4. 작업 실행 플로우

### 4.1. 정상 실행 시나리오

1. 스케줄러가 크론 표현식 확인
2. 작업이 실행 가능 상태인지 확인
3. 의존성 확인 (선행 작업 완료 여부)
4. 리소스 가용성 확인
5. 작업 실행
6. 실행 결과 기록
7. 후속 작업 트리거


### 4.2. 실패 복구 시나리오

1. 작업 실행 실패
2. 실패 로그 기록
3. 재시도 정책에 따라 대기
4. 재시도 실행
5. 최대 재시도 횟수 초과 시
   - 실패 작업 격리
   - 관리자 알림
   - 시스템 상태 업데이트


## 5. 모니터링 및 로깅

### 5.1. 모니터링 지표
```yaml
시스템 상태:
  - 작업 실행 성공률
  - 평균 실행 시간
  - 대기 중인 작업 수
  - 동시 실행 작업 수
  - 리소스 사용률

작업 상태:
  - 대기 중
  - 실행 중
  - 성공
  - 실패
  - 재시도 중


### 5.2. 로그 레벨

DEBUG: 디버깅 정보
INFO: 정상 작업 로그
WARNING: 주의 필요 상황
ERROR: 작업 실패
CRITICAL: 시스템 장애


## 6. 보안 고려사항

### 6.1. 접근 제어
- RBAC(Role-Based Access Control) 구현
- API 키 기반 인증
- 작업 실행 권한 분리

### 6.2. 데이터 보호
- 작업 간 데이터 격리
- 민감 정보 암호화
- 로그 데이터 익명화

## 7. 확장성 계획

### 7.1. 수평적 확장
- 다중 스케줄러 인스턴스
- 작업 분산 처리
- 로드 밸런싱

### 7.2. 기능 확장
- 사용자 정의 작업 추가
- 플러그인 아키텍처
- 외부 시스템 연동

## 8. 결론

AEGIS Scheduler v3.1은 다음과 같은 개선사항을 제공합니다:

1. **정확한 실행**: 정밀한 크론 표현식을 통한 시간 관리
2. **안정성 향상**: 의존성 관리와 실패 복구 메커니즘
3. **효율성 개선**: 리소스 관리와 우선순위 시스템
4. **실용성 강화**: 휴일 처리와 실제 트레이딩 환경 대응
5. **운영 편의성**: 종합적인 모니터링과 로깅 시스템

이 개선사항들은 AEGIS 시스템의 신뢰성과 효율성을 크게 향상시킬 것입니다.

---
**문서 버전**: v3.1  
**최종 업데이트**: 2024년  
**관련 문서**: AEGIS_ARCHITECTURE.md, AEGIS_API_SPEC.md

