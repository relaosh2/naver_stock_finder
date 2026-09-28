import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import FinanceDataReader as fdr
import requests
from datetime import datetime, timedelta

from data_fetcher import get_stock_list, fetch_naver_stock_info, fetch_stock_ohlcv
from technical_indicators import analyze_technical_indicators, calculate_rsi, calculate_bollinger_bands
from scanner import run_stock_scan

# 페이지 기본 설정
st.set_page_config(
    page_title="갓성호님의 바닥에서 난 잡아",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS 스타일링
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F3F4F6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3B82F6;
    }
    .score-badge-high {
        background-color: #DCFCE7;
        color: #166534;
        padding: 0.2rem 0.6rem;
        border-radius: 0.375rem;
        font-weight: 600;
    }
    .score-badge-mid {
        background-color: #FEF9C3;
        color: #854D0E;
        padding: 0.2rem 0.6rem;
        border-radius: 0.375rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📊 갓성호님의 바닥에서 난 잡아</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">단순한 낙주가 아닌 <b>[52주 최저가/과매도 바닥 + 외인/기관 수급 + 거래량 급증 + 저평가 밸류]</b>가 결합된 <b>상승 반등 유력 종목</b>을 탐색합니다.</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 사이드바: 검색 필터 및 조건 설정
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 탐색 조건 설정")

market_choice = st.sidebar.selectbox("대상 시장", ["전체 (KOSPI + KOSDAQ)", "코스피 (KOSPI)", "코스닥 (KOSDAQ)"])
market_map = {"전체 (KOSPI + KOSDAQ)": "ALL", "코스피 (KOSPI)": "KOSPI", "코스닥 (KOSDAQ)": "KOSDAQ"}
selected_market = market_map[market_choice]

top_n = st.sidebar.slider("시가총액 상위 스캔 범위", min_value=30, max_value=500, value=150, step=10, 
                         help="시가총액 상위 N개 종목을 대상으로 분석을 수행합니다. (스캔 종목 수가 많을수록 시간이 더 소요됩니다)")

min_score = st.sidebar.slider("최소 반등 점수 (Score)", min_value=35, max_value=85, value=45, step=5,
                             help="70점 이상: 강력 반등 유망 / 55점 이상: 반등 신호 포착 / 40점 이상: 바닥 관심")

with st.sidebar.expander("⚙️ 세부 필터 옵션", expanded=False):
    max_diff_low = st.slider("52주 최저가 대비 최대 이격률(%)", min_value=3, max_value=35, value=20, help="현재가가 52주 최저가 대비 N% 이내인 종목만 필터링")
    req_foreign_buy = st.checkbox("외국인 최근 3일 순매수 종목만", value=False)
    req_organ_buy = st.checkbox("기관 최근 3일 순매수 종목만", value=False)
    req_double_buy = st.checkbox("외인+기관 쌍끌이 순매수 종목만", value=False)
    req_vol_surge = st.checkbox("거래량 급증 (20일 평균의 1.3배 이상)", value=False)
    req_low_pbr = st.checkbox("저평가 PBR 1.0 이하만", value=False)

# -----------------------------------------------------------------------------
# 스캔 실행 버튼 및 상태 관리
# -----------------------------------------------------------------------------
if 'scan_data' not in st.session_state:
    st.session_state.scan_data = None

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    start_scan = st.button("🚀 바닥 반등 종목 스캔 시작", type="primary", use_container_width=True)

if start_scan:
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(curr, total):
        pct = int((curr / total) * 100)
        progress_bar.progress(pct)
        status_text.text(f"종목 수집 및 반등 확률 분석 중... ({curr}/{total} 완료)")
        
    start_time = datetime.now()
    df_result = run_stock_scan(market=selected_market, top_n=top_n, progress_callback=update_progress)
    elapsed = (datetime.now() - start_time).total_seconds()
    
    progress_bar.empty()
    status_text.empty()
    st.session_state.scan_data = df_result
    st.success(f"총 {len(df_result)}개의 바닥 관심/반등 후보 종목이 발굴되었습니다. (소요시간: {elapsed:.1f}초)")

# -----------------------------------------------------------------------------
# 결과 표시 및 필터링
# -----------------------------------------------------------------------------
df = st.session_state.scan_data

if df is not None and not df.empty:
    filtered_df = df[df['total_score'] >= min_score].copy()
    filtered_df = filtered_df[filtered_df['diff_from_52w_low_pct'] <= max_diff_low]
    
    if req_foreign_buy:
        filtered_df = filtered_df[filtered_df['foreign_buy_3d'] > 0]
    if req_organ_buy:
        filtered_df = filtered_df[filtered_df['organ_buy_3d'] > 0]
    if req_double_buy:
        filtered_df = filtered_df[(filtered_df['foreign_buy_3d'] > 0) & (filtered_df['organ_buy_3d'] > 0)]
    if req_vol_surge:
        filtered_df = filtered_df[filtered_df['vol_surge_ratio'] >= 1.3]
    if req_low_pbr:
        filtered_df = filtered_df[filtered_df['pbr'] <= 1.0]

    st.markdown(f"### 🎯 조건 만족 종목 ({len(filtered_df)}건)")

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.metric("발굴된 종목 수", f"{len(filtered_df)} 개")
    with m_col2:
        high_potential = len(filtered_df[filtered_df['total_score'] >= 70])
        st.metric("강력 반등 유력 (70점 이상)", f"{high_potential} 개")
    with m_col3:
        double_buy_cnt = len(filtered_df[(filtered_df['foreign_buy_3d'] > 0) & (filtered_df['organ_buy_3d'] > 0)])
        st.metric("외인+기관 쌍끌이 매수", f"{double_buy_cnt} 개")
    with m_col4:
        vol_surge_cnt = len(filtered_df[filtered_df['vol_surge_ratio'] >= 1.5])
        st.metric("거래량 급증(1.5배+) 종목", f"{vol_surge_cnt} 개")

    table_display = filtered_df.copy()
    table_display['52주 최저가 이격률'] = table_display['diff_from_52w_low_pct'].apply(lambda x: f"+{x:.1f}%")
    table_display['52주 최고가 낙폭'] = table_display['fall_from_52w_high_pct'].apply(lambda x: f"{x:.1f}%")
    table_display['외인 3일 순매수(주)'] = table_display['foreign_buy_3d'].apply(lambda x: f"{x:+,}")
    table_display['기관 3일 순매수(주)'] = table_display['organ_buy_3d'].apply(lambda x: f"{x:+,}")
    table_display['거래량 증가율'] = table_display['vol_surge_ratio'].apply(lambda x: f"{x:.2f}배")
    table_display['PBR'] = table_display['pbr'].apply(lambda x: f"{x:.2f}배" if pd.notnull(x) else "-")
    table_display['PER'] = table_display['per'].apply(lambda x: f"{x:.1f}배" if pd.notnull(x) else "-")
    table_display['현재가'] = table_display['current_price'].apply(lambda x: f"{x:,}원")
    
    cols_to_show = [
        'code', 'name', 'market', 'grade', 'total_score', '현재가', 
        '52주 최저가 이격률', '52주 최고가 낙폭', 'rsi', '거래량 증가율', 
        '외인 3일 순매수(주)', '기관 3일 순매수(주)', 'PBR'
    ]
    rename_dict = {
        'code': '종목코드',
        'name': '종목명',
        'market': '시장',
        'grade': '등급',
        'total_score': '반등점수',
        'rsi': 'RSI(14)'
    }
    
    st.dataframe(
        table_display[cols_to_show].rename(columns=rename_dict),
        use_container_width=True,
        hide_index=True
    )

    csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 검색 결과 CSV 다운로드 (엑셀 호환)",
        data=csv_data,
        file_name=f"바닥_반등_유망주_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

    st.markdown("---")
    st.markdown("### 🔍 종목별 심층 차트 & 반등 근거 분석")
    
    stock_options = [f"{row['name']} ({row['code']}) - {row['total_score']}점 [{row['grade']}]" for _, row in filtered_df.iterrows()]
    if stock_options:
        selected_stock_label = st.selectbox("상세 분석할 종목을 선택하세요", stock_options)
        selected_code = selected_stock_label.split("(")[1].split(")")[0]
        selected_row = filtered_df[filtered_df['code'] == selected_code].iloc[0]
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.markdown(f"#### 📌 **{selected_row['name']}** ({selected_row['code']})")
            st.markdown(f"- **시장**: {selected_row['market']}")
            st.markdown(f"- **현재가**: `{selected_row['current_price']:,}원`")
            st.markdown(f"- **반등 점수**: **`{selected_row['total_score']} / 100점`** ({selected_row['grade']})")
            st.markdown(f"- **네이버 금융 바로가기**: [네이버 증권 페이지로 이동 ↗]({selected_row['naver_link']})")
            
            st.markdown("##### 💡 반등 핵심 포인트 & 포착 사유")
            for r in selected_row['reasons']:
                st.markdown(f"- {r}")
                
            st.markdown("##### 📊 주요 밸류에이션 및 수급")
            st.markdown(f"- **PBR**: `{selected_row['pbr']}배` | **PER**: `{selected_row['per']}배`")
            st.markdown(f"- **최근 3일 외인 순매수**: `{selected_row['foreign_buy_3d']:+,} 주` (연속 {selected_row['foreign_consec']}일)")
            st.markdown(f"- **최근 3일 기관 순매수**: `{selected_row['organ_buy_3d']:+,} 주` (연속 {selected_row['organ_consec']}일)")
            
        with c2:
            df_chart = fetch_stock_ohlcv(selected_code, days=120)
            if df_chart is not None and len(df_chart) > 0:
                df_chart['MA5'] = df_chart['Close'].rolling(5).mean()
                df_chart['MA20'] = df_chart['Close'].rolling(20).mean()
                df_chart['MA60'] = df_chart['Close'].rolling(60).mean()
                df_chart['RSI'] = calculate_rsi(df_chart['Close'], 14)
                upper, mid, lower, _ = calculate_bollinger_bands(df_chart['Close'], 20, 2.0)
                df_chart['BB_Upper'] = upper
                df_chart['BB_Lower'] = lower
                
                fig = make_subplots(
                    rows=3, cols=1, 
                    shared_xaxes=True, 
                    vertical_spacing=0.04,
                    subplot_titles=(f"{selected_row['name']} 일봉 차트 (볼린저밴드/이평선)", "거래량", "RSI (14)"),
                    row_heights=[0.6, 0.2, 0.2]
                )
                
                fig.add_trace(go.Candlestick(
                    x=df_chart.index,
                    open=df_chart['Open'],
                    high=df_chart['High'],
                    low=df_chart['Low'],
                    close=df_chart['Close'],
                    name="주가",
                    increasing_line_color='#EF4444',
                    decreasing_line_color='#3B82F6'
                ), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA5'], name="5일선", line=dict(color='orange', width=1)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA20'], name="20일선", line=dict(color='green', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA60'], name="60일선", line=dict(color='purple', width=1)), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_Upper'], name="BB 상단", line=dict(color='rgba(150,150,150,0.5)', dash='dot')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_Lower'], name="BB 하단", line=dict(color='rgba(239,68,68,0.7)', dash='dash')), row=1, col=1)
                
                colors = ['#EF4444' if c >= o else '#3B82F6' for c, o in zip(df_chart['Close'], df_chart['Open'])]
                fig.add_trace(go.Bar(
                    x=df_chart.index,
                    y=df_chart['Volume'],
                    name="거래량",
                    marker_color=colors
                ), row=2, col=1)
                
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['RSI'], name="RSI(14)", line=dict(color='#8B5CF6')), row=3, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="red", row=3, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="green", row=3, col=1)
                
                fig.update_layout(
                    height=600,
                    margin=dict(l=20, r=20, t=30, b=20),
                    showlegend=False,
                    xaxis_rangeslider_visible=False
                )
                
                st.plotly_chart(fig, use_container_width=True)

else:
    if not start_scan:
        st.info("👈 왼쪽 상단의 **[🚀 바닥 반등 종목 스캔 시작]** 버튼을 눌러 스캔을 진행해 주세요.")
