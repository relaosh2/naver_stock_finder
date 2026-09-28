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
        
        # 이름 필터링 (스팩, ETN, ETF, 리츠 등 제외)
        exclude_keywords = ['스팩', 'SPAC', 'ETF', 'ETN', '리츠', '호', '우B', '우C']
        pattern = '|'.join(exclude_keywords)
        df = df[~df['name'].str.contains(pattern, na=False, case=False)]
        
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
        "dividend_yield": None
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
