# AEGIS v3.1 - KIS API 통합 명세서

## 문서 개요
이 문서는 한국투자증권(KIS) Open API를 기반으로 한 **AEGIS(Automated Equity & Global Investment System) v3.1**의 통합 명세서입니다. 시스템의 설계 철학, 성능 최적화 전략, 장애 대응 체계 및 운영 가이드를 포함합니다.

---

## 1. 아키텍처 개요 및 설계 원칙

### 1.1 핵심 설계 철학
- **Source of Truth 원칙**: 모든 거래 데이터의 원본은 중앙 데이터베이스에서 관리하며, API는 상태 동기화의 매개체 역할만 수행합니다.
- **계층적 추상화**: 데이터 접근 계층(DAL), 비즈니스 로직 계층(BLL), 표현 계층(Presentation Layer)을 명확히 분리합니다.
- **이벤트 주도 아키텍처**: 실시간 시장 데이터와 주문 체결은 이벤트 기반으로 처리하여 시스템 반응성을 극대화합니다.

### 1.2 통신 프로토콜 비교: REST vs WebSocket
| 항목 | REST API | WebSocket |
|------|----------|-----------|
| **사용 목적** | 단발성 조회, 주문 전송 | 실시간 시세, 체결 실시간 수신 |
| **연결 방식** | Stateless, 요청-응답 | Persistent, 양방향 |
| **부하 영향** | 호출 수에 비례 | 연결 수와 메시지 빈도에 비례 |
| **권장 사용처** | 계좌 조회, 일괄 주문, 거래 내역 | 호가/체결 스트리밍, 주문 체결 실시간 감지 |
| **타임아웃** | 연결/읽기 타임아웃 5초 | 핑/퐁 메커니즘으로 연결 유지 |

---

## 2. 성능 최적화 전략

### 2.1 커넥션 풀링 (HTTP/WebSocket)
```yaml
HTTP Client Pool:
  maxTotal: 50
  maxPerRoute: 20
  validateAfterInactivity: 5000ms
  connectionTimeToLive: 300s

WebSocket Pool:
  maxConnections: 10  # 계정별 제한
  reconnectInterval: 1000ms
  heartbeatInterval: 30000ms
```

### 2.2 API 호출 배칭 및 스로틀링
- **배칭**: 동일 계정의 다수 주문은 `OVC_ORDER` (일괄주문) TR을 활용하여 단일 요청으로 처리합니다.
- **스로틀링**: 초당 최대 30회 호출 제한 (KIS 서버 제약 준수).
- **우선순위 큐**: 시장가 주문은 지정가 주문보다 높은 우선순위를 부여합니다.

### 2.3 캐싱 전략 (Redis/Memcached)
```python
CACHE_LAYERS = {
    "L1": "Local Cache (Guava/Caffeine) - TTL 1초",
    "L2": "Central Redis Cluster - TTL 30초",
    "CACHEABLE_DATA": [
        "주식기본정보(MST)",
        "계좌평가잔고",
        "전일종가",
        "반복조회 TR (5초 내 동일파라미터)"
    ]
}
```

---

## 3. 장애 대응 및 복구 체계

### 3.1 Circuit Breaker 패턴 (Resilience4j/Hystrix)
```java
CircuitBreakerConfig config = CircuitBreakerConfig.custom()
    .slidingWindowSize(10)
    .failureRateThreshold(50.0f)
    .waitDurationInOpenState(Duration.ofSeconds(30))
    .permittedNumberOfCallsInHalfOpenState(5)
    .build();
// 적용 대상: 실시간 호가 조회, 주문 전송 API
```

### 3.2 Fallback 메커니즘
- **1차 Fallback**: 로컬 캐시 데이터 반환 (최근 성공 응답).
- **2차 Fallback**: 대체거래소(NXT)로 라우팅 (지원되는 상품 한정).
- **최종 Fallback**: 사용자 정의 안전값 반환 및 관리자 알림.

### 3.3 재시도 정책 (Exponential Backoff)
```yaml
retryPolicy:
  maxAttempts: 3
  initialInterval: 1000ms
  multiplier: 2.0
  maxInterval: 10000ms
  retryableExceptions:
    - SocketTimeoutException
    - ConnectionPoolTimeoutException
    - 5xx Server Errors
```

---

## 4. 모니터링 및 관측 가능성

### 4.1 메트릭 수집 (Prometheus/Grafana)
- **지연시간**: API 응답 시간(99th percentile), WebSocket 메시지 지연.
- **호출량**: 분당/시간당 TR 호출 수, 실패율.
- **시스템 자원**: 커넥션 풀 사용률, 쓰레드 풀 대기 큐 크기.

### 4.2 분산 추적 (Jaeger/OpenTelemetry)
- 모든 외부 호출에 `X-Trace-Id` 주입.
- 트레이스 내부에 TR 코드, 계좌번호(마스킹), 응답 코드 포함.

### 4.3 알림 설정 (PagerDuty/Slack)
```yaml
alerts:
  - trigger: "실시간 시세 연결 끊김 > 30초"
    severity: P1
    channel: #trading-alerts
    
  - trigger: "주문 실패율 > 10% (5분간)"
    severity: P2
    channel: #system-health
    
  - trigger: "일일 허용 오더 한도 80% 도달"
    severity: P3
    channel: #risk-notification
```

---

## 5. 보안 강화 정책

### 5.1 키 관리 및 로테이션
- **자동 로테이션**: 액세스 토큰 6시간, 리프레시 토큰 30일 주기 갱신.
- **안전한 저장**: 키는 HSM 또는 AWS KMS를 통해 암호화하여 저장.
- **RBAC 적용**: API 키별 권한 분리 (조회 전용, 주문 가능).

### 5.2 감사 로깅
모든 주요 행위는 감사 로그에 아래 정보와 함께 기록됩니다:
- 사용자 ID (마스킹)
- TR 코드 및 파라미터
- IP 주소 및 요청 시간
- 처리 결과 및 오류 코드
- 보존 기간: 7년 (금융 거래 관련 법률 준수)

### 5.3 네트워크 보안
- **IP 화이트리스트**: KIS API 서버와의 통신은 사전 등록된 IP에서만 허용.
- **VPC 엔드포인트**: 퍼블릭 인터넷 노출 최소화.
- **TLS 1.3**: 모든 통신에 강화된 암호화 프로토콜 적용.

---

## 6. 테스트 가이드

### 6.1 모의투자 환경 설정
```bash
# 모의투자 API 엔드포인트
REST: https://openapivts.koreainvestment.com:29443
WebSocket: wss://openapivts.koreainvestment.com:8443

# 모의계정 발급 필수 (실거래 계정과 분리)
# 모의투자 전용 appkey, appsecret 사용
```

### 6.2 테스트 케이스 체크리스트
- [ ] 단일 주문 정상 처리 (시장가/지정가)
- [ ] 일괄 주문 정상 처리
- [ ] 실시간 호가 정상 구독 및 수신
- [ ] 주문 체결 실시간 감지
- [ ] 계좌 잔고/평가 조회
- [ ] 오류 시나리오 (잔고부족, 유효하지않은종목코드 등)
- [ ] 재연결 시나리오 (네트워크 끊김 후 복구)

### 6.3 부하 테스트 시나리오
- 동시 사용자 100명 기준, 초당 10건 주문 처리 검증.
- WebSocket 연결 50개 유지 상태에서 메시지 지연 < 100ms 확인.
- 24시간 내내 지속적인 호가 구독 및 주문 시뮬레이션.

---

## 7. 스마트 주문 시스템

### 7.1 호가 오프셋 전략
```python
def calculate_order_price(market_type, side, base_price):
    OFFSET = {
        "KOSPI": {"buy": -0.02, "sell": 0.02},      # 호가 단위 1% 적용
        "KOSDAQ": {"buy": -0.03, "sell": 0.03},     # 호가 단위 1% 적용
        "ELW": {"buy": -0.01, "sell": 0.01}         # 변동성 고려
    }
    return base_price * (1 + OFFSET[market_type][side])
```

### 7.2 주문 유형별 처리 전략
| 주문 유형 | 오프셋 적용 | 타임아웃 | 재시도 |
|-----------|-------------|----------|--------|
| **시장가** | 없음 | 2초 | 없음 |
| **지정가** | 동적 오프셋 | 5초 | 2회 (가격 조정) |
| **조건부** | 없음 | 즉시 | 없음 (서버내부처리) |

---

## 8. NXT(대체거래소) 연동

### 8.1 자동 라우팅 규칙
```yaml
routing_rules:
  - condition: "KIS API 응답시간 > 2000ms"
    action: "NXT로 자동 전환"
    
  - condition: "KIS 주문 실패 (오류코드 8xx)"
    action: "NXT 폴백 발동"
    
  - condition: "유동성 낮은 종목(거래량 < 1000주)"
    action: "NXT 우선 라우팅"
```

### 8.2 동기화 메커니즘
- 주문 상태 이중 기록 (KIS ↔ NXT)
- 5초 간격으로 미체결 주문 동기화
- 체결 보고는 먼저 도착하는 시스템 기준으로 확정

---

## 9. API 버전 관리

### 9.1 버전 호환성 정책
- **Major 버전**: 하위 호환성 없는 변경 (v3 → v4)
- **Minor 버전**: 하위 호환성 있는 기능 추가 (v3.0 → v3.1)
- **Patch 버전**: 버그 수정 및 성능 개선 (v3.1.0 → v3.1.1)

### 9.2 마이그레이션 가이드 (v3.0 → v3.1)
1. **이전 버전 API 지원**: `/api/v3.0/` 엔드포인트 6개월간 병행 운영
2. **점진적 전환**: 모니터링 대시보드에서 v3.1 호출 비율 확인
3. **롤백 계획**: 주요 이상 시 5분 내 v3.0으로 복구 가능해야 함
4. **변경사항**:
   - `TR: t1101` 응답 필드 추가 (`marketCap`)
   - WebSocket 프로토콜 업그레이드 (압축 방식 변경)
   - 오류 코드 추가 (`901: 주문 배칭 실패`)

---

## 10. 운영 체크리스트

### 10.1 일일 점검 항목
- [ ] API 키 만료 여부 확인 (만료 7일 전 알림)
- [ ] 일일 호출 한도 사용량 모니터링 (<80%)
- [ ] 실시간 연결 건강 상태 (연결 끊김 이벤트 < 5회/일)
- [ ] 주문 성공률 (> 99.5%) 및 평균 응답시간 (< 500ms)

### 10.2 장애 발생 시 대응 절차
1. **1분 내**: Circuit Breaker 자동 차단, Fallback 활성화
2. **5분 내**: 원인 분석 (KIS 상태 페이지 확인, 내부 로그 검토)
3. **15분 내**: 대체 수단(NXT) 통한 서비스 지속성 확보
4. **30분 내**: 고객사 CS팀에 상태 보고 및 예상 복구 시간 공유

---

## 부록 A: TR 코드 참조표
| TR 코드 | 설명 | 권장 캐시 TTL |
|---------|------|---------------|
| `t1101` | 주식 현재가 | 1초 |
| `t1305` | 기간별 주가 | 30분 |
| `t0424` | 주문체결내역 | 실시간 |
| `t8412` | 차트데이터 | 5분 |

## 부록 B: 오류 코드 핸들링
| 오류 코드 | 의미 | 권장 조치 |
|-----------|------|-----------|
| `1` | 정상처리 | - |
| `2` | 주문실패 | 로그 기록, 관리자 알림 |
| `8` | 접속실패 | 재연결 시도 (최대 3회) |
| `9` | 처리지연 | 사용자에게 진행중 메시지 표시 |

---

**문서 버전**: v3.1.0  
**최종 업데이트**: 2024년 1월  
**적용 대상**: AEGIS 트레이딩 시스템 v3.1 이상  
**문서 관리자**: 시스템 아키텍처 팀
```
