def analyze_short_sale_status(tech_data: dict, naver_info: dict) -> dict:
    """
    공매도 및 수급 기반 숏커버링(Short Squeeze) 및 공매도 리스크 종합 분석
    """
    f_buy = naver_info.get("foreign_buy_3d", 0)
    o_buy = naver_info.get("organ_buy_3d", 0)
    f_consec = naver_info.get("foreign_consecutive_buy", 0)
    o_consec = naver_info.get("organ_consecutive_buy", 0)
    
    vol_surge = tech_data.get("vol_surge_ratio", 1.0)
    diff_low = tech_data.get("diff_from_52w_low_pct", 50.0)
    rsi = tech_data.get("rsi", 50.0)
    
    # 숏커버링 (Short Squeeze) 유망 조건:
    # 1) 52주 최저가 부근 (+15% 이내)
    # 2) 외인 또는 기관 순매수 유입 (최근 3일 > 0)
    # 3) 거래량 급증 (20일 평균 대비 1.3배 이상)
    is_short_squeeze = (diff_low <= 15.0) and (f_buy > 0 or o_buy > 0) and (vol_surge >= 1.3)
    
    if is_short_squeeze and (f_buy > 0 and o_buy > 0):
        status = "🔥 숏커버링(숏퀴즈) 강력 유망"
        badge_color = "#DCFCE7"
        text_color = "#15803D"
        desc = "바닥권 거래량 폭증과 함께 공매도 세력의 손절성 숏커버링(환매수) 및 외인·기관 쌍끌이 유입 중"
    elif is_short_squeeze:
        status = "⚡ 숏커버링 반등 신호 포착"
        badge_color = "#E0F2FE"
        text_color = "#0369A1"
        desc = "52주 최저가 부근 거래량 폭증으로 공매도 숏커버링(매수 환매수) 유입 가능성 높음"
    elif f_buy > 0 and o_buy > 0:
        status = "🛡️ 공매도 안전지대 (쌍끌이 유입)"
        badge_color = "#F0FDF4"
        text_color = "#166534"
        desc = "외인·기관 동시 순매수로 공매도 압박이 최소화되고 수급이 우량한 상태"
    elif f_buy < 0 and o_buy < 0:
        status = "⚠️ 공매도·매도 출하 주의"
        badge_color = "#FEE2E2"
        text_color = "#991B1B"
        desc = "외국인 및 기관 동시 순매도로 공매도 및 매도 물량 출회 압박 존재"
    else:
        status = "📊 공매도 압박 중립"
        badge_color = "#F1F5F9"
        text_color = "#475569"
        desc = "수급 및 공매도 추이 중립 횡보 구간"

    return {
        "short_status": status,
        "short_badge_color": badge_color,
        "short_text_color": text_color,
        "short_desc": desc,
        "is_short_squeeze": is_short_squeeze
    }
