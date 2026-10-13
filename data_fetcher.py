import requests
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://m.stock.naver.com"
}

def get_stock_list(market: str = "ALL") -> pd.DataFrame:
    """
    코스피/코스닥 상장 종목 목록 수집 및 기본 필터링
    market: 'ALL', 'KOSPI', 'KOSDAQ'
    """
    try:
        df = fdr.StockListing('KRX')
        
        # 1. 컬럼 정형화
        # Code, Name, Market, Marcap(시가총액), Stocks(상장주식수), Close, ChangeCode 등
        cols_map = {
            'Code': 'code',
            'Name': 'name',
            'Market': 'market',
            'Marcap': 'marcap',
            'Stocks': 'stocks',
            'Close': 'close',
            'Dept': 'dept',
            'Sector': 'sector'
        }
        df = df.rename(columns={k: v for k, v in cols_map.items() if k in df.columns})
        
        # 2. 시장 필터
        if market == 'KOSPI':
            df = df[df['market'].isin(['KOSPI', 'STK'])]
        elif market == 'KOSDAQ':
            df = df[df['market'].isin(['KOSDAQ', 'KSQ'])]
            
        # 3. 비정상/우선주/스팩/ETN/ETF 필터링
        # 6자리 숫자가 아닌 종목 제외
        df = df[df['code'].astype(str).str.len() == 6]
        # 보통주는 끝자리가 0 (우선주는 5, 7, 9 등)
        df = df[df['code'].astype(str).str.endswith('0')]
        
        # 이름 필터링 (스팩, ETN, ETF, 리츠, 투자주의/관리/경고 등 제외)
        exclude_keywords = ['스팩', 'SPAC', 'ETF', 'ETN', '리츠', '호', '우B', '우C', '관리', '주의', '경고', '위험', '환기', '정지']
        pattern = '|'.join(exclude_keywords)
        df = df[~df['name'].str.contains(pattern, na=False, case=False)]
        
        # Dept(소속부) 필터링 (관리종목, 투자주의, 투자경고, 투자위험, 환기종목 제외)
        if 'dept' in df.columns:
            dept_pattern = '관리|주의|경고|위험|환기|정지'
            df = df[~df['dept'].astype(str).str.contains(dept_pattern, na=False, case=False)]
        
        # 시가총액 기준 내림차순 정렬 (유동성 있는 종목 우선)
        if 'marcap' in df.columns:
            df['marcap'] = pd.to_numeric(df['marcap'], errors='coerce').fillna(0)
            df = df.sort_values(by='marcap', ascending=False)
            
        return df.reset_index(drop=True)
    except Exception as e:
        print(f"Error fetching stock list: {e}")
        return pd.DataFrame()

def fetch_naver_stock_info(code: str) -> dict:
    """
    네이버 증권 모바일 API를 통해 종목의 수급(외인/기관) 및 기본 밸류에이션(PBR/PER) 수집
    """
    info = {
        "code": code,
        "foreign_buy_3d": 0,
        "organ_buy_3d": 0,
        "foreign_consecutive_buy": 0,
        "organ_consecutive_buy": 0,
        "pbr": None,
        "per": None,
        "market_cap_str": "",
        "dividend_yield": None,
        "is_restricted": False
    }
    
    # 1. 외인/기관 수급 트렌드 (최근 5일)
    try:
        url_trend = f"https://m.stock.naver.com/api/stock/{code}/trend"
        res = requests.get(url_trend, headers=HEADERS, timeout=3)
        if res.status_code == 200:
            trends = res.json()
            if isinstance(trends, list) and len(trends) > 0:
                f_buys = []
                o_buys = []
                for item in trends[:5]:
                    f_qty = item.get("foreignerPureBuyQuant", "0").replace(",", "").replace("+", "")
                    o_qty = item.get("organPureBuyQuant", "0").replace(",", "").replace("+", "")
                    try:
                        f_buys.append(int(f_qty))
                    except:
                        f_buys.append(0)
                    try:
                        o_buys.append(int(o_qty))
                    except:
                        o_buys.append(0)
                
                # 최근 3일 누적 순매수
                info["foreign_buy_3d"] = sum(f_buys[:3])
                info["organ_buy_3d"] = sum(o_buys[:3])
                
                # 연속 순매수 일수 계산
                f_consec = 0
                for v in f_buys:
                    if v > 0:
                        f_consec += 1
                    else:
                        break
                info["foreign_consecutive_buy"] = f_consec
                
                o_consec = 0
                for v in o_buys:
                    if v > 0:
                        o_consec += 1
                    else:
                        break
                info["organ_consecutive_buy"] = o_consec
    except Exception:
        pass
        
    # 2. 통합 정보 (PBR, PER 등)
    try:
        url_integ = f"https://m.stock.naver.com/api/stock/{code}/integration"
        res2 = requests.get(url_integ, headers=HEADERS, timeout=3)
        if res2.status_code == 200:
            data2 = res2.json()
            
            # 관리종목 / 거래정지 / 투자주의 / 투자경고 / 투자위험 종목 상태 감지
            stock_state = data2.get("stockState", {}) or {}
            trade_stop = data2.get("tradeStopState", False)
            if trade_stop or stock_state.get("isManagement") or stock_state.get("isCaution") or stock_state.get("isWarning") or stock_state.get("isRisk"):
                info["is_restricted"] = True

            total_infos = data2.get("totalInfos", [])
            for item in total_infos:
                key = item.get("key", "")
                val = item.get("value", "")
                if "PBR" in key or key == "PBR":
                    try:
                        info["pbr"] = float(val.replace("배", "").replace(",", "").strip())
                    except:
                        pass
                elif "PER" in key or key == "PER":
                    try:
                        info["per"] = float(val.replace("배", "").replace(",", "").strip())
                    except:
                        pass
                elif "시가총액" in key:
                    info["market_cap_str"] = val
                elif "배당수익률" in key:
                    try:
                        info["dividend_yield"] = float(val.replace("%", "").replace(",", "").strip())
                    except:
                        pass
    except Exception:
        pass
        
    return info

def fetch_stock_ohlcv(code: str, days: int = 150) -> pd.DataFrame:
    """
    종목의 일봉 데이터(OHLCV) 수집
    """
    try:
        # 네이버 금융 일봉 스크래핑 또는 FDR
        start_date = (pd.Timestamp.now() - pd.Timedelta(days=days * 2)).strftime("%Y-%m-%d")
        df = fdr.DataReader(code, start=start_date)
        if df is not None and len(df) > 0:
            return df
    except Exception:
        pass
    return None


def fetch_market_briefing() -> dict:
    """
    실시간 코스피(KOSPI) / 코스닥(KOSDAQ) 지수 및 투자자별(개인/외인/기관) 매매동향 브리핑 수집
    """
    result = {}
    for code in ["KOSPI", "KOSDAQ"]:
        item = {
            "close": "-",
            "change": "0.00",
            "pct": 0.0,
            "status": "",
            "personal": "0",
            "foreign": "0",
            "organ": "0"
        }
        try:
            r_basic = requests.get(f"https://m.stock.naver.com/api/index/{code}/basic", headers=HEADERS, timeout=3)
            if r_basic.status_code == 200:
                b = r_basic.json()
                item["close"] = b.get("closePrice", "-")
                item["change"] = b.get("compareToPreviousClosePrice", "0.00")
                try:
                    item["pct"] = float(b.get("fluctuationsRatio", 0.0))
                except Exception:
                    item["pct"] = 0.0
                item["status"] = "장중 실시간" if b.get("marketStatus") == "OPEN" else "장마감"

            r_trend = requests.get(f"https://m.stock.naver.com/api/index/{code}/trend", headers=HEADERS, timeout=3)
            if r_trend.status_code == 200:
                t = r_trend.json()
                item["personal"] = t.get("personalValue", "0")
                item["foreign"] = t.get("foreignValue", "0")
                item["organ"] = t.get("institutionalValue", "0")
        except Exception:
            pass
        result[code] = item

    # 시황 한줄 진단 생성
    kp_pct = result.get("KOSPI", {}).get("pct", 0.0)
    kd_pct = result.get("KOSDAQ", {}).get("pct", 0.0)
    avg_pct = (kp_pct + kd_pct) / 2.0

    if avg_pct <= -2.5:
        comment = "🚨 지수 급락(투매) 구간! 우량주 과매도 바닥 줍줍 및 외인·기관 역발상 매집 종목에 주목하세요."
        mood_bg = "#FEF2F2"
        mood_color = "#B91C1C"
    elif avg_pct <= -0.7:
        comment = "📉 약세장 조정 흐름입니다. 지수 대비 하방 경직성이 강하고 기관·외인 수급이 유입되는 종목 위주로 대응하세요."
        mood_bg = "#EFF6FF"
        mood_color = "#1D4ED8"
    elif avg_pct >= 1.2:
        comment = "🔥 강세장 랠리 진행 중! 거래량이 터지며 바닥에서 고개를 드는 쌍끌이 수급 종목의 탄력이 강해집니다."
        mood_bg = "#ECFDF5"
        mood_color = "#047857"
    else:
        comment = "⚖️ 보합·종목별 차별화 장세입니다. 철저히 수급(외인·기관)과 저평가(저PBR) 바닥 시그널 위주로 선별 공략하세요."
        mood_bg = "#F8FAFC"
        mood_color = "#334155"

    result["comment"] = comment
    result["mood_bg"] = mood_bg
    result["mood_color"] = mood_color
    return result

