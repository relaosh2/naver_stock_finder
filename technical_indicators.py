import pandas as pd
import numpy as np

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI(상대강도지수) 계산"""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0):
    """볼린저 밴드 (상단, 중심, 하단, %B) 계산"""
    ma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = ma + (std * num_std)
    lower = ma - (std * num_std)
    percent_b = (series - lower) / (upper - lower + 1e-9)
    return upper, ma, lower, percent_b

def analyze_technical_indicators(df: pd.DataFrame) -> dict:
    """
    일봉 데이터(OHLCV)를 기반으로 바닥 및 반등 시그널 분석
    """
    if df is None or len(df) < 30:
        return {}

    df = df.copy()
    close = df['Close']
    volume = df['Volume']
    
    # 1. 이동평균선
    df['MA5'] = close.rolling(5).mean()
    df['MA20'] = close.rolling(20).mean()
    df['MA60'] = close.rolling(60).mean()
    
    # 2. RSI
    df['RSI14'] = calculate_rsi(close, 14)
    
    # 3. 볼린저 밴드
    upper, ma, lower, pct_b = calculate_bollinger_bands(close, 20, 2.0)
    df['BB_Upper'] = upper
    df['BB_Mid'] = ma
    df['BB_Lower'] = lower
    df['BB_PctB'] = pct_b
    
    # 4. 거래량 20일 이평
    df['Vol_MA20'] = volume.rolling(20).mean()
    
    curr = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else curr
    prev5 = df.iloc[-5] if len(df) >= 5 else curr
    
    # 52주 (약 250거래일) 고점/저점
    lookback = min(len(df), 250)
    high_52w = df['High'].tail(lookback).max()
    low_52w = df['Low'].tail(lookback).min()
    
    curr_close = float(curr['Close'])
    curr_low = float(curr['Low'])
    
    # 지표 계산
    diff_from_52w_low_pct = ((curr_close - low_52w) / (low_52w + 1e-9)) * 100
    fall_from_52w_high_pct = ((curr_close - high_52w) / (high_52w + 1e-9)) * 100
    
    curr_rsi = float(curr['RSI14']) if not np.isnan(curr['RSI14']) else 50.0
    prev_rsi = float(prev['RSI14']) if not np.isnan(prev['RSI14']) else 50.0
    
    # 거래량 급증률 (당일 거래량 / 20일 평균 거래량)
    vol_ma20 = float(curr['Vol_MA20']) if not np.isnan(curr['Vol_MA20']) and curr['Vol_MA20'] > 0 else float(curr['Volume'])
    vol_surge_ratio = float(curr['Volume']) / (vol_ma20 + 1e-9)
    
    # 골든크로스 여부 (5일선이 20일선 상향 돌파 또는 5일선 상승 반전)
    is_ma5_rising = curr['MA5'] > prev['MA5']
    is_golden_cross = (prev['MA5'] <= prev['MA20']) and (curr['MA5'] > curr['MA20'])
    is_above_ma5 = curr_close >= curr['MA5']
    
    # 볼린저 밴드 하단 지지 여부 (%B가 0~0.2 사이이거나 하단 터치 후 양봉 반등)
    bb_pct_b = float(curr['BB_PctB']) if not np.isnan(curr['BB_PctB']) else 0.5
    is_bb_lower_support = (bb_pct_b <= 0.25) or (prev['Low'] <= prev['BB_Lower'] and curr_close > curr['BB_Lower'])
    
    # 캔들 형태 (양봉 여부 및 밑꼬리 발생 여부)
    is_bullish = curr['Close'] >= curr['Open']
    body_size = abs(curr['Close'] - curr['Open'])
    lower_shadow = min(curr['Open'], curr['Close']) - curr['Low']
    is_hammer_candle = is_bullish and (lower_shadow >= body_size * 1.5) and (lower_shadow > 0)
    
    return {
        "current_price": curr_close,
        "volume": int(curr['Volume']),
        "vol_ma20": int(vol_ma20),
        "high_52w": high_52w,
        "low_52w": low_52w,
        "diff_from_52w_low_pct": diff_from_52w_low_pct,
        "fall_from_52w_high_pct": fall_from_52w_high_pct,
        "rsi": curr_rsi,
        "prev_rsi": prev_rsi,
        "rsi_rebound": (prev_rsi <= 32 and curr_rsi > prev_rsi),
        "vol_surge_ratio": vol_surge_ratio,
        "is_golden_cross": is_golden_cross,
        "is_ma5_rising": is_ma5_rising,
        "is_above_ma5": is_above_ma5,
        "bb_pct_b": bb_pct_b,
        "is_bb_lower_support": is_bb_lower_support,
        "is_bullish": is_bullish,
        "is_hammer_candle": is_hammer_candle,
        "df_processed": df
    }
