# AEGIS v3.0 - 중요한 설계 결정사항

## 1. Just-in-Time Data Feeding (핵심 결정!)

**배경**: Brain AI가 오래된 데이터를 분석하면 "뒷북" → 무의미한 결과

**결정**: 데이터 수집을 AI 분석 직전(0.1초 이내)에 수행

```python
# ❌ 잘못된 순서
await brain.analyze()   # 1시간 전 데이터
await fetcher.sync()    # 늦음!

# ✅ 올바른 순서
await fetcher.sync()    # 지금!
await db.commit()       # 0.1초
await brain.analyze()   # 최신!
```

**근거**: "brain-ai 실행을 위해선 fetcher kis dart krx 가 새로운 데이터를 가져와야하잖아 그래야 의미가 있지않아?"

## 2. Dynamic Schedule (10-60-30 전략)

**배경**: 30분 고정 간격은 평균값일 뿐, 수익률 최적값 아님

**결정**: 시간대별 차등 실행
- 🔥 오전장 (09:00~10:00): 10분 (70% 변동성)
- 💤 점심장 (10:00~13:00): 60분 (저거래량)
- 🌤️ 오후장 (13:00~15:00): 20분 (추세 확인)
- 🏁 막판 (15:00~15:20): 10분 (마지막 기회)

**근거**: 시장 활동 패턴에 맞춤, 예상 수익률 +15~25%

## 3. Write/Read Only Pattern (엄격 준수)

**배경**: v2에서 여러 모듈이 KIS API를 직접 호출해서 혼란

**결정**: 
- ✅ Write: KISFetcher만 DB에 쓰기
- ✅ Read: 모든 모듈은 DB만 읽기
- ⚠️ 예외: OrderService만 주문 직전 실시간 잔고 확인

**근거**: Single Source of Truth, 데이터 일관성

## 4. 3-Layer Monitoring

**배경**: WebSocket 40개 슬롯 제한, 2000종목 모니터링 필요

**결정**: 계층별 역할 분담
- Layer 3: DeepSeek R1 전체 분석 (07:20, 2000종목)
- Layer 2: Market Scanner (1분, gemini, ~100종목)
- Layer 1: WebSocket 실시간 (40 슬롯, Priority 1/2/3)

**근거**: 슬롯 제한 극복, 효율적 모니터링

## 5. Priority 기반 WebSocket 구독

**배경**: 40개 슬롯으로 모든 종목 구독 불가

**결정**: 우선순위 기반 자동 관리
- Priority 1: 보유종목 (항상 유지)
- Priority 2: AI Daily Picks (DeepSeek R1)
- Priority 3: 급등주 (가장 먼저 제거)

**근거**: 중요한 종목 놓치지 않음, 동적 슬롯 교체

## 6. NXT Market Support

**배경**: KIS API가 NXT와 KRX를 별도 TR_ID로 분리

**결정**: 
- TR_ID_MAP으로 KRX/NXT 분기
- NXT 시장가 주문 차단 (지정가만)
- get_combined_balance()로 통합 조회

**근거**: NXT 시장 지원, 안전한 주문 실행

## 7. 5단계 파이프라인

**배경**: 데이터 수집 → AI 분석 → 주문 실행 순서 보장 필요

**결정**: 명확한 5단계
1. Fetching - 최신 데이터 수집
2. Pre-processing - DB 저장
3. Brain - AI 분석
4. Validation - 시나리오 검증
5. Execution - 주문 실행

**근거**: 순서 보장, 단계별 에러 처리

## 8. Scenario Validator 통합 검증 (중요!)

**배경**: AI 예측만으로는 불충분, 검증 필요

**결정**: 3가지 검증 기법 통합
1. **시나리오 검증** - AI 예측 시나리오별 분석
2. **백테스트** - 과거 데이터로 전략 검증
3. **몬테카를로 시뮬레이션** - 확률적 리스크 분석

**근거**: 단순 과거 패턴 비교보다 강력, 리스크 최소화

**구현 방향**:
- 시나리오: Best/Expected/Worst case 분석
- 백테스트: 최근 3개월 유사 패턴 승률 계산
- 몬테카를로: 1000회 시뮬레이션으로 확률 분포 계산
- 통합 점수: 세 가지 결과 종합해서 승인/거부 결정
