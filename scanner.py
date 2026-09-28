import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from data_fetcher import get_stock_list, fetch_naver_stock_info, fetch_stock_ohlcv
from technical_indicators import analyze_technical_indicators
from rebound_scorer import calculate_rebound_score
import time

def scan_single_stock(row):
    code = str(row['code']).zfill(6)
    name = row.get('name', '')
    market = row.get('market', '')
    marcap = row.get('marcap', 0)
    
    # 1. 일봉 데이터 조회
    df_ohlcv = fetch_stock_ohlcv(code, days=120)
    if df_ohlcv is None or len(df_ohlcv) < 30:
        return None
        
    # 2. 기술적 지표 분석
    tech_data = analyze_technical_indicators(df_ohlcv)
    if not tech_data:
        return None
        
    # 52주 최저가 대비 너무 높게 오른 종목(예: +50% 초과)은 바닥 스캔에서 1차 패스
    if tech_data.get('diff_from_52w_low_pct', 999) > 50.0:
        return None
        
    # 3. 네이버 수급 및 펀더멘털 조회
    naver_info = fetch_naver_stock_info(code)
    
    # 4. 반등 점수 계산
    score_result = calculate_rebound_score(tech_data, naver_info)
    
    return {
        "code": code,
        "name": name,
        "market": market,
        "current_price": int(tech_data['current_price']),
        "diff_from_52w_low_pct": round(tech_data['diff_from_52w_low_pct'], 1),
        "fall_from_52w_high_pct": round(tech_data['fall_from_52w_high_pct'], 1),
        "rsi": round(tech_data['rsi'], 1),
        "vol_surge_ratio": round(tech_data['vol_surge_ratio'], 2),
        "foreign_buy_3d": naver_info['foreign_buy_3d'],
        "organ_buy_3d": naver_info['organ_buy_3d'],
        "foreign_consec": naver_info['foreign_consecutive_buy'],
        "organ_consec": naver_info['organ_consecutive_buy'],
        "pbr": naver_info['pbr'],
        "per": naver_info['per'],
        "dividend_yield": naver_info['dividend_yield'],
        "total_score": score_result['total_score'],
        "grade": score_result['grade'],
        "reasons": score_result['reasons'],
        "marcap": marcap,
        "naver_link": f"https://finance.naver.com/item/main.naver?code={code}"
    }

def run_stock_scan(market="ALL", top_n=200, progress_callback=None) -> pd.DataFrame:
    """
    시장(KOSPI, KOSDAQ, ALL)의 시총 상위 top_n개 종목을 대상으로 바닥 반등 종목 스캔
    """
    df_stocks = get_stock_list(market=market)
    if df_stocks.empty:
        return pd.DataFrame()
        
    target_stocks = df_stocks.head(top_n).to_dict('records')
    total_count = len(target_stocks)
    
    results = []
    completed = 0
    
    # 병렬 처리 (최대 10개 스레드)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(scan_single_stock, row): row for row in target_stocks}
        for future in as_completed(futures):
            completed += 1
            if progress_callback:
                progress_callback(completed, total_count)
            try:
                res = future.result()
                if res and res['total_score'] >= 35: # 의미 있는 점수 이상만 수집
                    results.append(res)
            except Exception as e:
                pass
                
    if not results:
        return pd.DataFrame()
        
    df_res = pd.DataFrame(results)
    df_res = df_res.sort_values(by="total_score", ascending=False).reset_index(drop=True)
    return df_res

if __name__ == "__main__":
    print("Scanning top 30 stocks for testing...")
    df_test = run_stock_scan("ALL", top_n=30)
    print(f"Scanned result count: {len(df_test)}")
    if not df_test.empty:
        print(df_test[['code', 'name', 'total_score', 'grade', 'diff_from_52w_low_pct', 'rsi', 'foreign_buy_3d']].head(10))
