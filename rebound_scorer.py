import pandas as pd
import numpy as np
from technical_indicators import analyze_technical_indicators

def calculate_rebound_score(tech_data: dict, naver_info: dict, trend_info: dict = None) -> dict:
    """
    바닥 여부 및 향후 상승 확률(반등 스코어) 종합 산출
    - 총점 100점 만점
    """
    if not tech_data:
        return {"total_score": 0, "grade": "분석 불가", "reasons": []}
    
    score = 0
    reasons = []
    
    # -------------------------------------------------------------
    # 1. 최신 시장 트렌드 & 뉴스 이슈 가산점 (-10 ~ +15점)
    # -------------------------------------------------------------
    if trend_info:
        t_score = trend_info.get("trend_score", 0)
        score += t_score
        pos_r = trend_info.get("pos_reasons", [])
        neg_r = trend_info.get("neg_reasons", [])
        for pr in pos_r:
            reasons.append(pr)
        for nr in neg_r:
            reasons.append(nr)
    
    # -------------------------------------------------------------
    # 1. 바닥성 점수 (총 35점)
    # -------------------------------------------------------------
    diff_low_pct = tech_data.get("diff_from_52w_low_pct", 999)
    fall_high_pct = tech_data.get("fall_from_52w_high_pct", 0)
    bb_pct_b = tech_data.get("bb_pct_b", 0.5)
    
    # 1-1. 52주 최저가 대비 이격도 (최대 20점)
    if diff_low_pct <= 5.0:
        score += 20
        reasons.append(f"52주 최저가 대비 +{diff_low_pct:.1f}% 근접 (초근접 바닥권)")
    elif diff_low_pct <= 10.0:
        score += 15
        reasons.append(f"52주 최저가 대비 +{diff_low_pct:.1f}% (바닥권 형성)")
    elif diff_low_pct <= 20.0:
        score += 10
        reasons.append(f"52주 최저가 대비 +{diff_low_pct:.1f}% (저점 반등 초입)")
    elif diff_low_pct <= 30.0:
        score += 5
        
    # 1-2. 고점 대비 하락폭 (최대 10점)
    if fall_high_pct <= -45.0:
        score += 10
        reasons.append(f"52주 최고가 대비 {fall_high_pct:.1f}% 낙폭 과대")
    elif fall_high_pct <= -30.0:
        score += 5
        reasons.append(f"52주 최고가 대비 {fall_high_pct:.1f}% 충분한 가격 조정")
        
    # 1-3. 볼린저 밴드 하단 지지 (최대 5점)
    if tech_data.get("is_bb_lower_support"):
        score += 5
        reasons.append("볼린저 밴드 하단선 지지 및 반등 시도")

    # -------------------------------------------------------------
    # 2. 반등 모멘텀 & 수급 (총 45점) - 상승 확률을 결정짓는 핵심
    # -------------------------------------------------------------
    f_buy = naver_info.get("foreign_buy_3d", 0)
    o_buy = naver_info.get("organ_buy_3d", 0)
    f_consec = naver_info.get("foreign_consecutive_buy", 0)
    o_consec = naver_info.get("organ_consecutive_buy", 0)
    vol_ratio = tech_data.get("vol_surge_ratio", 1.0)
    rsi = tech_data.get("rsi", 50)
    
    # 2-1. 외국인 / 기관 수급 (최대 20점)
    if f_buy > 0 and o_buy > 0:
        score += 15
        reasons.append("🔥 외인 & 기관 동시 순매수 (쌍끌이 유입)")
    elif f_buy > 0 or o_buy > 0:
        score += 8
        buyer = "외국인" if f_buy > 0 else "기관"
        reasons.append(f"{buyer} 순매수 유입")
        
    if f_consec >= 2 or o_consec >= 2:
        score += 5
        consec_str = []
        if f_consec >= 2: consec_str.append(f"외인 {f_consec}일 연속 순매수")
        if o_consec >= 2: consec_str.append(f"기관 {o_consec}일 연속 순매수")
        reasons.append(f"📈 {' / '.join(consec_str)}")
        
    # 2-2. 거래량 급증 / 매집봉 (최대 15점)
    if vol_ratio >= 2.5:
        score += 15
        reasons.append(f"💥 바닥권 거래량 폭증 (평균 대비 {vol_ratio:.1f}배 - 매집 의심)")
    elif vol_ratio >= 1.5:
        score += 10
        reasons.append(f"거래량 증가세 (평균 대비 {vol_ratio:.1f}배)")
    elif vol_ratio >= 1.1:
        score += 5
        
    # 2-3. 기술적 반등 신호 (골든크로스 / RSI 반등) (최대 10점)
    if tech_data.get("rsi_rebound"):
        score += 5
        reasons.append(f"RSI({rsi:.1f}) 과매도권 탈출 반등 신호")
    elif rsi <= 35:
        score += 3
        reasons.append(f"RSI({rsi:.1f}) 단기 과매도 구간")
        
    if tech_data.get("is_golden_cross"):
        score += 5
        reasons.append("✨ 5일/20일선 단기 골든크로스 발생")
    elif tech_data.get("is_ma5_rising") and tech_data.get("is_above_ma5"):
        score += 3
        reasons.append("5일 이평선 상승 반전 및 주가 상회")
        
    if tech_data.get("is_hammer_candle"):
        score += 2
        reasons.append("바닥권 밑꼬리 양봉(해머형) 출현")

    # -------------------------------------------------------------
    # 3. 가치평가 및 안전성 (총 20점)
    # -------------------------------------------------------------
    pbr = naver_info.get("pbr")
    per = naver_info.get("per")
    div_yield = naver_info.get("dividend_yield")
    
    # PBR 점수 (최대 10점)
    if pbr is not None and pbr > 0:
        if pbr <= 0.6:
            score += 10
            reasons.append(f"초저평가 PBR {pbr:.2f}배 (강력한 자산 안전마진)")
        elif pbr <= 1.0:
            score += 7
            reasons.append(f"저평가 PBR {pbr:.2f}배 (순자산 미만)")
        elif pbr <= 1.5:
            score += 4
            
    # PER 및 배당 (최대 10점)
    if per is not None and 0 < per <= 12:
        score += 5
        reasons.append(f"저PER {per:.1f}배 (실적 대비 저평가)")
        
    if div_yield is not None and div_yield >= 2.5:
        score += 5
        reasons.append(f"배당수익률 {div_yield:.1f}% (배당 방어력 보유)")

    # -------------------------------------------------------------
    # 등급 분류
    # -------------------------------------------------------------
    if score >= 75:
        grade = "⭐ 강력 반등 유망"
    elif score >= 60:
        grade = "🎯 반등 신호 포착"
    elif score >= 45:
        grade = "👀 바닥 관심 관찰"
    else:
        grade = "일반/조정중"
        
    return {
        "total_score": min(score, 100),
        "grade": grade,
        "reasons": reasons,
        "details": {
            "diff_52w_low": diff_low_pct,
            "fall_52w_high": fall_high_pct,
            "rsi": rsi,
            "vol_surge": vol_ratio,
            "foreign_buy_3d": f_buy,
            "organ_buy_3d": o_buy,
            "pbr": pbr,
            "per": per,
            "dividend_yield": div_yield
        }
    }
