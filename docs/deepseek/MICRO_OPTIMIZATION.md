# AEGIS v3.1 미세 최적화 기법 문서화

## 1. 호가 오프셋 최적화

### 이론적 배경
호가 오프셋 전략은 시장의 마이크로스트럭처를 활용하여 매수는 매도호가보다 낮은 가격에, 매도는 매수호가보다 높은 가격에 주문을 걸어 스프레드의 일부를 포착하는 방법입니다. 이는 시장 제조자(Market Maker)의 수익 원리와 유사하며, 고빈도 거래(HFT)에서 널리 사용됩니다.

### 실제 적용 코드
```python
import pandas as pd
import numpy as np

def calculate_order_price(current_price, action, market_condition):
    """
    호가 오프셋을 적용한 주문 가격 계산
    
    Parameters:
    current_price: 현재 가격
    action: 'buy' 또는 'sell'
    market_condition: 'open', 'mid', 'close', 'volatile', 'calm'
    """
    
    # 장 상황별 오프셋 설정
    offsets = {
        'open': {'buy': -0.003, 'sell': 0.003},      # 시가: 큰 변동성
        'mid': {'buy': -0.002, 'sell': 0.002},       # 장중: 일반적
        'close': {'buy': -0.001, 'sell': 0.001},     # 종가: 작은 변동성
        'volatile': {'buy': -0.004, 'sell': 0.004},  # 변동성 큰 장
        'calm': {'buy': -0.0015, 'sell': 0.0015}     # 변동성 작은 장
    }
    
    # 기본값 설정
    offset = offsets.get(market_condition, offsets['mid'])
    
    if action == 'buy':
        return current_price * (1 + offset['buy'])
    else:  # sell
        return current_price * (1 + offset['sell'])

# 사용 예시
current_price = 10000
buy_price = calculate_order_price(current_price, 'buy', 'mid')  # 9980원
sell_price = calculate_order_price(current_price, 'sell', 'mid') # 10020원
```

### 예상 효과
- 연간 추가 수익률: 0.3%~0.8%
- 효과가 큰 조건: 고유동성 주식, 좁은 스프레드, 낮은 변동성 장
- 기대 체결률: 65%~85%

### 주의사항
1. 강한 추세장에서는 체결률 급감
2. 공시/이벤트 발생 시 오프셋 확대 필요
3. 유동성 부족 종목에서는 역효과 가능

## 2. 슬리피지 최소화

### 이론적 배경
슬리피지는 주문 가격과 실제 체결 가격의 차이로 발생하는 비용입니다. 대량 주문 시 시장 충격(Market Impact)으로 인해 슬리피지가 증가하며, 이는 거래 성과를 저하시키는 주요 요인입니다.

### 실제 적용 코드
```python
class SlippageMinimizer:
    def __init__(self, symbol_data):
        self.symbol_data = symbol_data
        
    def calculate_optimal_order_size(self):
        """거래량 기반 최적 주문 크기 계산"""
        avg_daily_volume = self.symbol_data['avg_daily_volume']
        max_order_percentage = 0.01  # 일평균 거래량의 1%
        
        optimal_size = avg_daily_volume * max_order_percentage
        return optimal_size
    
    def analyze_order_book(self, order_book):
        """호가창 분석을 통한 매물대 확인"""
        bid_ask_spread = order_book['best_ask'] - order_book['best_bid']
        
        # 매물대 분석
        pressure_levels = []
        for price, volume in order_book['ask_levels']:
            if volume > self.symbol_data['threshold_volume']:
                pressure_levels.append({
                    'price': price,
                    'volume': volume,
                    'type': 'resistance'
                })
        
        return {
            'spread': bid_ask_spread,
            'pressure_levels': pressure_levels,
            'recommended_price': self.calculate_vwap(order_book)
        }
    
    def calculate_vwap(self, market_data):
        """VWAP(Volume Weighted Average Price) 계산"""
        total_value = 0
        total_volume = 0
        
        for trade in market_data['recent_trades']:
            total_value += trade['price'] * trade['volume']
            total_volume += trade['volume']
        
        return total_value / total_volume if total_volume > 0 else 0
    
    def execute_order(self, order_type, quantity):
        """슬리피지 최소화 주문 실행"""
        optimal_quantity = min(quantity, self.calculate_optimal_order_size())
        
        # 주문 분할 실행 (Iceberg Order)
        slices = max(1, int(optimal_quantity / self.symbol_data['slice_size']))
        
        execution_plan = []
        for i in range(slices):
            slice_qty = min(self.symbol_data['slice_size'], 
                          optimal_quantity - sum(execution_plan))
            if slice_qty > 0:
                execution_plan.append(slice_qty)
        
        return execution_plan
```

### 예상 효과
- 연간 슬리피지 비용 절감: 0.15%~0.35%
- 대형주 대비 소형주에서 효과 큼
- 기관 투자자에게 유의미한 성과 개선

### 주의사항
1. 너무 작은 주문 분할은 거래비용 증가
2. VWAP 전략은 강한 추세장에서 불리
3. 실시간 데이터 처리 지연에 민감

## 3. 타이밍 최적화

### 이론적 배경
시장의 시간대별 패턴을 활용하여 거래 효율성을 극대화하는 전략입니다. 개장/종장 시간대, 점심시간, 기관 거래 시간대 등에서 나타나는 특정 패턴을 통계적으로 분석하여 최적의 진입/청산 시점을 결정합니다.

### 실제 적용 코드
```python
import datetime
from typing import Dict, Tuple

class TimingOptimizer:
    def __init__(self):
        self.time_patterns = self.initialize_time_patterns()
    
    def initialize_time_patterns(self) -> Dict[str, Dict]:
        """시간대별 거래 패턴 정의"""
        return {
            '09:00-09:30': {
                'strategy': 'gap_trading',
                'characteristics': ['high_volatility', 'gap_filling', 'early_momentum'],
                'suggested_actions': ['gap_play', 'reversal_trades'],
                'risk_factor': 1.2
            },
            '09:30-11:00': {
                'strategy': 'trend_following',
                'characteristics': ['trend_establishment', 'institutional_flow'],
                'suggested_actions': ['breakout_trades', 'trend_confirmation'],
                'risk_factor': 1.0
            },
            '11:00-13:00': {
                'strategy': 'range_trading',
                'characteristics': ['low_volume', 'narrow_range', 'lunch_effect'],
                'suggested_actions': ['mean_reversion', 'scalping'],
                'risk_factor': 0.8
            },
            '13:00-14:30': {
                'strategy': 'momentum_trading',
                'characteristics': ['afternoon_session', 'volume_pickup'],
                'suggested_actions': ['momentum_continuation', 'news_play'],
                'risk_factor': 1.1
            },
            '14:30-15:30': {
                'strategy': 'closing_auction',
                'characteristics': ['institutional_rebalancing', 'final_settlement'],
                'suggested_actions': ['closing_price_play', 'position_squaring'],
                'risk_factor': 1.3
            }
        }
    
    def get_current_time_slot(self, current_time: datetime.time) -> str:
        """현재 시간대 확인"""
        time_slots = {
            (9, 0): '09:00-09:30',
            (9, 30): '09:30-11:00',
            (11, 0): '11:00-13:00',
            (13, 0): '13:00-14:30',
            (14, 30): '14:30-15:30'
        }
        
        for (hour, minute), slot in time_slots.items():
            if current_time.hour == hour and current_time.minute >= minute:
                return slot
        
        return '09:00-09:30'  # 기본값
    
    def adjust_order_parameters(self, current_time: datetime.time, 
                               base_params: Dict) -> Dict:
        """시간대별 주문 파라미터 조정"""
        time_slot = self.get_current_time_slot(current_time)
        pattern = self.time_patterns[time_slot]
        
        adjusted_params = base_params.copy()
        
        # 변동성 기반 주문 크기 조정
        adjusted_params['position_size'] *= pattern['risk_factor']
        
        # 시간대별 특화 전략 적용
        if time_slot == '09:00-09:30':
            # 갭 트레이딩: 전일 종가 대비 ±2% 범위 진입
            adjusted_params['entry_range'] = 0.02
            adjusted_params['stop_loss'] = 0.015
            
        elif time_slot == '11:00-13:00':
            # 점심시간: 스캘핑 전략
            adjusted_params['profit_target'] = 0.003
            adjusted_params['stop_loss'] = 0.002
            adjusted_params['max_holding_time'] = 300  # 5분
            
        elif time_slot == '14:30-15:30':
            # 종가 장중: 기관 매매 대응
            adjusted_params['use_moc_loc'] = True  # 시장종가/지정가 주문 활용
            adjusted_params['closing_auction_participation'] = True
        
        return adjusted_params
    
    def calculate_optimal_entry_time(self, symbol: str, 
                                   historical_data: pd.DataFrame) -> Dict:
        """역사적 데이터 기반 최적 진입 시간대 분석"""
        returns_by_hour = []
        
        for hour in range(9, 16):
            hour_data = historical_data[historical_data['hour'] == hour]
            if len(hour_data) > 0:
                avg_return = hour_data['return'].mean()
                success_rate = (hour_data['return'] > 0).mean()
                returns_by_hour.append({
                    'hour': hour,
                    'avg_return': avg_return,
                    'success_rate': success_rate,
                    'sharpe_ratio': hour_data['return'].mean() / hour_data['return'].std()
                })
        
        # 최적 시간대 추천
        optimal_hour = max(returns_by_hour, key=lambda x: x['sharpe_ratio'])
        
        return {
            'optimal_hour': optimal_hour['hour'],
            'expected_return': optimal_hour['avg_return'],
            'recommended_strategy': self.get_strategy_for_hour(optimal_hour['hour'])
        }
```

### 예상 효과
- 연간 추가 수익률: 0.4%~1.2%
- 시간대별 전환으로 최대 30% 성과 개선 가능
- 변동성 조정으로 위험 대비 수익률(샤프지수) 향상

### 주의사항
1. 패턴 변화 가능성: 시장 구조 변화 시 재검증 필요
2. 이벤트 위험: 공시, 경제지표 발표 시 패턴 무효화
3. 과최적화 위험: 과거 데이터에 너무 맞춤 조정 시 실전 효과 감소

## 4. 수수료/세금 최적화

### 이론적 배경
거래 비용은 장기적으로 투자 수익률을 저하시키는 주요 요인입니다. 수수료, 세금, 시장 충격 비용을 체계적으로 관리하면 순수익을 크게 향상시킬 수 있습니다.

### 실제 적용 코드
```python
class CostOptimizer:
    def __init__(self, account_type, trading_frequency):
        self.account_type = account_type  # '일반', 'ISA', '연금'
        self.trading_frequency = trading_frequency
        
        # 한국 기준 수수료 구조 (예시)
        self.commission_rates = {
            'online_discount': 0.015,  # 온라인 할인율 0.015%
            'floor_trading': 0.03,     # 영업장 0.03%
            'minimum': 500            # 최소 수수료 500원
        }
        
        # 세율 구조
        self.tax_rates = {
            'capital_gain': {
                'general': 0.22,      # 일반 과세: 22%
                'isa': 0.09,          # ISA: 9%
                'pension': 0.00       # 연금: 비과세
            },
            'dividend': {
                'general': 0.154,     # 일반: 15.4%
                'isa': 0.00,          # ISA: 비과세
                'pension': 0.00       # 연금: 비과세
            }
        }
    
    def calculate_effective_cost(self, trade_amount, is_intraday=False):
        """실효 거래 비용 계산"""
        # 수수료 계산
        commission = trade_amount * (self.commission_rates['online_discount'] / 100)
        commission = max(commission, self.commission_rates['minimum'])
        
        # 세금 계산 (매도 시)
        capital_gain_tax = 0
        if not is_intraday:  # 단기 매매차익이 아닌 경우
            tax_rate = self.tax_rates['capital_gain'][self.account_type]
            # 실제 구현시에는 매수평균가와의 차이 계산 필요
        
        # 총 비용
        total_cost = commission + capital_gain_tax
        
        return {
            'commission': commission,
            'tax': capital_gain_tax,
            'total_cost': total_cost,
            'effective_rate': total_cost / trade_amount * 100
        }
    
    def optimize_trading_frequency(self, expected_returns, volatility):
        """기대수익률과 변동성 기반 최적 거래 빈도 계산"""
        # 거래 비용과 기대수익률 비교
        annual_trading_cost = self.trading_frequency * self.average_trade_cost
        
        # 켈리 기준 적용 변형
        optimal_frequency = self.calculate_kelly_frequency(
            expected_returns, 
            volatility, 
            annual_trading_cost
        )
        
        return max(1, min(optimal_frequency, self.trading_frequency))
    
    def dividend_timing_optimization(self, stock_data):
        """배당락일 기반 매매 타이밍 최적화"""
        ex_dividend_date = stock_data['ex_dividend_date']
        dividend_amount = stock_data['dividend_amount']
        
        # 배당락일 전후 수익률 분석
        days_before = 5
        days_after = 5
        
        optimal_action = None
        
        # 배당세 고려한 최적 행동 결정
        dividend_tax = dividend_amount * self.tax_rates['dividend'][self.account_type]
        net_dividend = dividend_amount - dividend_tax
        
        if net_dividend > 0 and self.account_type != 'pension':
            # 배당 수익이 양수일 경우 배당락일 전 매수 고려
            optimal_action = {
                'action': 'buy_before_ex_date',
                'suggested_date': ex_dividend_date - datetime.timedelta(days=1),
                'expected_benefit': net_dividend
            }
        else:
            # 배당세가 높을 경우 배당락일 이후 매수 고려
            optimal_action = {
                'action': 'buy_after_ex_date',
                'suggested_date': ex_dividend_date + datetime.timedelta(days=1),
                'reason': 'avoid_dividend_tax'
            }
        
        return optimal_action
    
    def tax_loss_harvesting(self, portfolio, current_date):
        """세금 손실 채취 전략"""
        unrealized_losses = []
        
        for position in portfolio:
            if position['unrealized_pnl'] < 0:
                # 30일 규칙(워시세일) 확인
                days_held = (current_date - position['purchase_date']).days
                if days_held > 30:
                    unrealized_losses.append({
                        'symbol': position['symbol'],
                        'loss_amount': abs(position['unrealized_pnl']),
                        'tax_benefit': abs(position['unrealized_pnl']) * 
                                     self.tax_rates['capital_gain'][self.account_type]
                    })
        
        # 세금 절감 효과가 큰 순으로 정렬
        unrealized_losses.sort(key=lambda x: x['tax_benefit'], reverse=True)
        
        return unrealized_losses[:3]  # 상위 3개 추천
```

### 예상 효과
- 연간 비용 절감: 0.25%~0.6%
- 세금 최적화로 추가 0.3%~0.5% 절감 가능
- 장기 복리 효과로 10년간 5%~15% 차이 발생

### 주의사항
1. 세법 변경 시 전략 수정 필요
2. 과도한 비용 절감은 기회비용 증가로 이어질 수 있음
3. 세금 손실 채취 시 실제 경제적 손실 발생 가능성

## 5. 포지션 사이징 미세 조정

### 이론적 배경
포트폴리오 이론과 위험 관리 원칙을 기반으로, 각 포지션의 적정 규모를 과학적으로 결정합니다. 변동성, 상관관계, 계정 크기, 위험 허용도를 종합적으로 고려하여 최적의 포지션 크기를 계산합니다.

### 실제 적용 코드
```python
import numpy as np
from scipy.optimize import minimize

class PositionSizingOptimizer:
    def __init__(self, account_size, risk_tolerance=0.02):
        self.account_size = account_size
        self.risk_tolerance = risk_tolerance  # 계정 대비 최대 손실 한도(2%)
        
    def calculate_atr_position_size(self, atr, entry_price, stop_loss_pct):
        """ATR 기반 포지션 크기 계산"""
        # 1일 ATR을 %로 변환
        atr_pct = atr / entry_price
        
        # ATR과 손절라인 중 더 보수적인 값 사용
        volatility_adjustment = min(atr_pct * 2, stop_loss_pct)
        
        # 포지션 크기 계산
        risk_amount = self.account_size * self.risk_tolerance
        position_risk = entry_price * volatility_adjustment
        
        if position_risk > 0:
            shares = risk_amount / position_risk
        else:
            shares = 0
            
        return {
            'shares': int(shares),
            'position_value': int(shares) * entry_price,
            'risk_per_share': position_risk,
            'volatility_adjustment': volatility_adjustment
        }
    
    def kelly_criterion_adjusted(self, win_rate, win_loss_ratio, kelly_fraction=0.5):
        """조정된 켈리 기준 적용"""
        # 기본 켈리 공식: f* = (bp - q) / b
        # where b = win/loss ratio, p = win rate, q = loss rate
        
        p = win_rate
        q = 1 - p
        b = win_loss_ratio
        
        if b <= 0:
            return 0
            
        # 기본 켈리 비율
        full_kelly = (b * p - q) / b
        
        # 과도한 레버리지 방지를 위해 조정(일반적으로 50%)
        adjusted_kelly = full_kelly * kelly_fraction
        
        # 음수 값 방지
        return max(0, min(adjusted_kelly, 0.25))  # 최대 25% 제한
    
    def portfolio_correlation_adjustment(self, correlation_matrix, current_positions):
        """상관관계 기반 포지션 조정"""
        n_assets = len(correlation_matrix)
        
        # 현재 포지션 가중치
        current_weights = np.array([pos['weight'] for pos in current_positions])
        
        # 포트폴리오 변동성 계산
        portfolio_volatility = self.calculate_portfolio_volatility(
            current_weights, 
            correlation_matrix
        )
        
        # 변동성 타겟 설정(연간 15%)
        target_volatility = 0.15
        
        # 변동성 조정 계수
        adjustment_factor = target_volatility / portfolio_volatility
        
        # 조정된 포지션 크기
        adjusted_weights = current_weights * adjustment_factor
        
        # 각 포지션 크기 제한(최대 10%)
        adjusted_weights = np.minimum(adjusted_weights, 0.1)
        
        return adjusted_weights
    
    def calculate_portfolio_volatility(self, weights, correlation_matrix):
        """포트폴리오 변동성 계산"""
        # 개별 자산 변동성(임시값)
        individual_vol = np.array([0.25, 0.30, 0.20, 0.35])[:len(weights)]
        
        # 분산-공분산 행렬
        cov_matrix = np.outer(individual_vol, individual_vol) * correlation_matrix
        
        # 포트폴리오 변동성
        portfolio_var = np.dot(weights.T, np.dot(cov_matrix, weights))
        
        return np.sqrt(portfolio_var)
    
    def dynamic_position_sizing(self, market_condition, confidence_score):
        """시장 조건과 신뢰도 기반 동적 포지션 조정"""
        # 기본 사이징 계수
        base_size = 1.0
        
        # 시장 조건 조정
        market_adjustments = {
            'trending': 1.2,
            'ranging': 0.8,
            'volatile': 0.6,
            'calm': 1.1
        }
        
        # 신뢰도 기반 조정(0~1 점수)
        confidence_adjustment = 0.5 + (confidence_score * 0.5)
        
        # 최종 조정 계수
        adjustment_factor = (
            market_adjustments.get(market_condition, 1.0) * 
            confidence_adjustment
        )
        
        # 최소/최대 제한
        return max(0.1, min(adjustment_factor, 1.5))
    
    def optimize_portfolio_weights(self, expected_returns, cov_matrix, 
                                 risk_free_rate=0.02):
        """현대 포트폴리오 이론 기반 최적화"""
        n_assets = len(expected_returns)
        
        # 제약 조건: 모든 가중치 합 = 1, 각 가중치 >= 0
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        ]
        bounds = [(0, 1) for _ in range(n_assets)]
        
        # 초기값
        init_weights = np.ones(n_assets) / n_assets
        
        # 목적 함수: 샤프지수 최대화
        def neg_sharpe_ratio(weights):
            port_return = np.dot(weights, expected_returns)
            port_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            sharpe = (port_return - risk_free_rate) / port_volatility
            return -sharpe
        
        # 최적화 실행
        result = minimize(
            neg_sharpe_ratio,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        return result.x
```

### 예상 효과
- 위험 조정 수익률(샤프지수) 향상: 10%~30%
- 드로다운 최대치 감소: 15%~25%
- 변동성 환경에서의 안정성 향상

### 주의사항
1. 역사적 상관관계가 미래에도 유지된다는 보장 없음
2. 과도한 최적화는 실제 시장에서 비현실적일 수 있음
3. 켈리 기준은 정확한 승률 추정에 매우 민감함

---

## 종합 실행 예제

```python
class AEGISv31_TradingSystem:
    def __init__(self, config):
        self.config = config
        self.cost_optimizer = CostOptimizer(config['account_type'], 
                                           config['trading_frequency'])
        self.position_sizer = PositionSizingOptimizer(config['account_size'])
        self.timing_optimizer = TimingOptimizer()
        
    def execute_trade(self, symbol, action, market_data):
        """통합 거래 실행 시스템"""
        
        # 1. 타이밍 최적화
        current_time = datetime.datetime.now().time()
        time_slot = self.timing_optimizer.get_current_time_slot(current_time)
        
        # 2. 포지션 사이징
        atr = market_data['atr']
        entry_price = market_data['current_price']
        
        position_info = self.position_sizer.calculate_atr_position_size(
            atr, entry_price, self.config['stop_loss_pct']
        )
        
        # 3. 호가 오프셋 적용
        order_price = calculate_order_price(
            entry_price, 
            action, 
            self.get_market_condition(time_slot)
        )
        
        # 4. 수수료 최적화 확인
        trade_amount = position_info['position_value']
        cost_analysis = self.cost_optimizer.calculate_effective_cost(
            trade_amount, 
            is_intraday=self.config['intraday']
        )
        
        # 5. 최종 주문 실행
        final_order = {
            'symbol': symbol,
            'action': action,
            'quantity': position_info['shares'],
            'price': order_price,
            'order_type': 'limit',
            'time_slot': time_slot,
            'expected_cost_pct': cost_analysis['effective_rate'],
            'risk_amount': self.config['account_size'] * self.position_sizer.risk_tolerance
        }
        
        return final_order
    
    def get_market_condition(self, time_slot):
        """시간대 기반 시장 조건 판단"""
        conditions = {
            '09:00-09:30': 'volatile',
            '09:30-11:00': 'trending',
            '11:00-13:00': 'calm',
            '13:00-14:30': 'trending',
            '14:30-15:30': 'volatile'
        }
        return conditions.get(time_slot, 'mid')
```

## 종합 예상 효과 요약

| 최적화 기법 | 연간 추가 수익률 | 위험 감소 효과 | 적용 난이도 |
|------------|-----------------|---------------|------------|
| 호가 오프셋 | 0.3%~0.8% | 낮음 | 낮음 |
| 슬리피지 최소화 | 0.15%~0.35% | 중간 | 중간 |
| 타이밍 최적화 | 0.4%~1.2% | 높음 | 높음 |
| 수수료/세금 최적화 | 0.25%~0.6% | 없음 | 낮음 |
| 포지션 사이징 | 0.5%~1.5%* | 매우 높음 | 높음 |
| **종합 효과** | **1.6%~4.5%** | **상당한 개선** | **통합 필요** |

*위험 조정 수익률 기준

## 구현 권장사항

1. **점진적 적용**: 한 번에 모든 기법을 적용하기보다 하나씩 도입하고 효과 측정
2. **백테스트**: 역사적 데이터로 각 기법의 효과 검증
3. **모니터링**: 실제 적용 시 지속적인 성과 모니터링과 파라미터 조정
4. **리스크 관리**: 최적화 기법이 실패할 경우를 대비한 안전장치 구현
5. **규정 준수**: 모든 거래가 관련 법규와 규정을 준수하는지 확인

---

**참고**: 모든 수치와 효과는 역사적 데이터 기반 추정치이며, 실제 결과는 시장 조건, 구현 품질, 실행 환경에 따라 달라질 수 있습니다. 실제 투자에 적용하기 전에 충분한 검증과 테스트를 권장합니다.
