import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime
import json

from data_fetcher import get_stock_list, fetch_naver_stock_info, fetch_stock_ohlcv
from technical_indicators import analyze_technical_indicators, calculate_rsi, calculate_bollinger_bands
from scanner import run_stock_scan
from kakao_notifier import send_kakao_stock_alert, KAKAO_REST_API_KEY

# -----------------------------------------------------------------------------
# 비밀번호 설정 및 보안 로직
# -----------------------------------------------------------------------------
APP_PASSWORD = "6101fks!"

st.set_page_config(
    page_title="📈 갓성호님의 바닥에서 난 잡아",
    page_icon="📱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 세션 인증 확인
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 모바일 PWA 메타 태그 & 커스텀 CSS 스타일링
st.markdown("""
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#1E3A8A">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="apple-touch-icon" href="https://img.icons8.com/color/96/line-chart.png">
</head>
<style>
    .stApp {
        background-color: #F8FAFC;
    }
    .mobile-header {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        padding: 16px;
        border-radius: 12px;
        color: white;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .mobile-title {
        font-size: 1.35rem;
        font-weight: 800;
        margin: 0;
        color: white;
    }
    .mobile-sub {
        font-size: 0.85rem;
        color: #E0F2FE;
        margin-top: 4px;
    }
    .stock-card {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .stock-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 8px;
        margin-bottom: 8px;
    }
    .stock-name {
        font-size: 1.1rem;
        font-weight: 700;
        color: #0F172A;
    }
    .stock-code {
        font-size: 0.8rem;
        color: #64748B;
    }
    .badge-score-high {
        background-color: #DCFCE7;
        color: #15803D;
        padding: 4px 8px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
    }
    .badge-score-mid {
        background-color: #FEF9C3;
        color: #A16207;
        padding: 4px 8px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
    }
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
        margin-top: 6px;
    }
    .metric-item {
        background-color: #F8FAFC;
        padding: 8px;
        border-radius: 8px;
        font-size: 0.82rem;
    }
    .metric-label {
        color: #64748B;
        font-size: 0.75rem;
    }
    .metric-val {
        color: #0F172A;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .naver-btn {
        display: block;
        width: 100%;
        text-align: center;
        background-color: #03C75A;
        color: white !important;
        font-weight: bold;
        padding: 10px;
        border-radius: 8px;
        text-decoration: none;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 비밀번호 미인증 시 화면
# -----------------------------------------------------------------------------
if not st.session_state.authenticated:
    st.markdown("""
    <div class="mobile-header" style="text-align: center;">
        <div class="mobile-title">🔒 갓성호님의 바닥에서 난 잡아</div>
        <div class="mobile-sub">보안 잠금 모바일 주식 시스템</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("##### 🔑 비밀번호를 입력해주세요")
    pwd_input = st.text_input("비밀번호", type="password", key="pwd_field")
    
    if st.button("🔓 앱 열기", type="primary", use_container_width=True):
        if pwd_input == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ 비밀번호가 올바르지 않습니다.")
            
    st.stop()

# -----------------------------------------------------------------------------
# 모바일 메인 헤더
# -----------------------------------------------------------------------------
st.markdown("""
<div class="mobile-header">
    <div class="mobile-title">📱 갓성호님의 바닥에서 난 잡아</div>
    <div class="mobile-sub">52주 최저가/과매도 + 외인·기관 수급 유입 + 거래량 급증 탐색</div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 세션 상태 관리
# -----------------------------------------------------------------------------
if 'scan_data' not in st.session_state:
    st.session_state.scan_data = None
if 'active_preset' not in st.session_state:
    st.session_state.active_preset = "ALL"

# -----------------------------------------------------------------------------
# 전략 터치 프리셋 (Quick Pills)
# -----------------------------------------------------------------------------
st.markdown("##### ⚡ 1-Tap 추천 전략 프리셋")
p_col1, p_col2, p_col3, p_col4 = st.columns(4)

with p_col1:
    if st.button("🔥 쌍끌이", use_container_width=True, help="외국인+기관 동시 순매수"):
        st.session_state.active_preset = "DOUBLE"
with p_col2:
    if st.button("💥 거래량", use_container_width=True, help="거래량 1.5배 이상 폭증"):
        st.session_state.active_preset = "VOL"
with p_col3:
    if st.button("🛡️ 저PBR", use_container_width=True, help="PBR 1.0 이하 저평가"):
        st.session_state.active_preset = "PBR"
with p_col4:
    if st.button("⚡ 과매도", use_container_width=True, help="RSI 35 이하 단기과매도"):
        st.session_state.active_preset = "RSI"

# -----------------------------------------------------------------------------
# 검색 옵션 & 필터 (접이식 Expander)
# -----------------------------------------------------------------------------
with st.expander("⚙️ **스캔 필터 & 카카오 알림 설정**", expanded=False):
    market_choice = st.selectbox("대상 시장", ["전체 (KOSPI + KOSDAQ)", "코스피 (KOSPI)", "코스닥 (KOSDAQ)"])
    market_map = {"전체 (KOSPI + KOSDAQ)": "ALL", "코스피 (KOSPI)": "KOSPI", "코스닥 (KOSDAQ)": "KOSDAQ"}
    selected_market = market_map[market_choice]

    top_n = st.slider("시총 상위 탐색 범위", min_value=30, max_value=300, value=100, step=10)
    min_score = st.slider("최소 반등 점수", min_value=35, max_value=85, value=45, step=5)

    req_foreign_buy = st.checkbox("외국인 최근 3일 순매수", value=(st.session_state.active_preset == "DOUBLE"))
    req_organ_buy = st.checkbox("기관 최근 3일 순매수", value=(st.session_state.active_preset == "DOUBLE"))
    req_double_buy = st.checkbox("외인+기관 쌍끌이 순매수", value=(st.session_state.active_preset == "DOUBLE"))
    req_vol_surge = st.checkbox("거래량 급증 (20일 평균 1.3배+)", value=(st.session_state.active_preset == "VOL"))
    req_low_pbr = st.checkbox("저평가 PBR 1.0 이하만", value=(st.session_state.active_preset == "PBR"))

    st.markdown("---")
    st.markdown("##### 💬 카카오톡 알림 연동")
    kakao_token_user = st.text_input("카카오톡 Access Token (선택)", value="", type="password", help="REST API 키: " + KAKAO_REST_API_KEY[:6] + "***")
    
    if st.button("💬 테스트 종목 카카오톡 메시지 전송", use_container_width=True):
        sample_stock = {
            "code": "005930",
            "name": "삼성전자",
            "total_score": 75,
            "current_price": 65000,
            "diff_from_52w_low_pct": 3.2,
            "foreign_buy_3d": 1250000,
            "organ_buy_3d": 850000,
            "grade": "⭐ 강력 반등 유망",
            "reasons": ["🔥 외인 & 기관 동시 순매수 (쌍끌이 유입)", "바닥권 거래량 폭증 (평균 대비 2.1배 - 매집 의심)", "RSI(28.5) 과매도권 탈출 반등 신호"]
        }
        tk = kakao_token_user if kakao_token_user else KAKAO_REST_API_KEY
        ok = send_kakao_stock_alert(tk, sample_stock)
        if ok:
            st.success("✅ 카카오톡 알림 메시지가 성공적으로 발송되었습니다!")
        else:
            st.info("💡 카카오 동의항목(talk_message) 설정 후 수신 가능합니다.")

# -----------------------------------------------------------------------------
# 스캔 실행 버튼
# -----------------------------------------------------------------------------
start_scan = st.button("🚀 **바닥 반등 종목 스캔 시작**", type="primary", use_container_width=True)

if start_scan:
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(curr, total):
        pct = int((curr / total) * 100)
        progress_bar.progress(pct)
        status_text.text(f"종목 수집 및 반등 분석 중... ({curr}/{total} 완료)")

    start_time = datetime.now()
    df_result = run_stock_scan(market=selected_market, top_n=top_n, progress_callback=update_progress)
    elapsed = (datetime.now() - start_time).total_seconds()

    progress_bar.empty()
    status_text.empty()
    st.session_state.scan_data = df_result
    st.toast(f"✅ {len(df_result)}개 종목 발굴 완료! ({elapsed:.1f}초)", icon="📈")

# -----------------------------------------------------------------------------
# 결과 모바일 종목 카드 리스트
# -----------------------------------------------------------------------------
df = st.session_state.scan_data

if df is not None and not df.empty:
    filtered_df = df[df['total_score'] >= min_score].copy()

    if req_foreign_buy:
        filtered_df = filtered_df[filtered_df['foreign_buy_3d'] > 0]
    if req_organ_buy:
        filtered_df = filtered_df[filtered_df['organ_buy_3d'] > 0]
    if req_double_buy:
        filtered_df = filtered_df[(filtered_df['foreign_buy_3d'] > 0) & (filtered_df['organ_buy_3d'] > 0)]
    if req_vol_surge:
        filtered_df = filtered_df[filtered_df['vol_surge_ratio'] >= 1.3]
    if req_low_pbr:
        filtered_df = filtered_df[filtered_df['pbr'].notnull() & (filtered_df['pbr'] <= 1.0)]

    st.markdown(f"### 🎯 조건 만족 종목 ({len(filtered_df)}건)")

    # 4대 메트릭 요약
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.metric("발굴 종목 수", f"{len(filtered_df)} 개")
    with m_col2:
        high_cnt = len(filtered_df[filtered_df['total_score'] >= 70])
        st.metric("강력 반등 (70점+)", f"{high_cnt} 개")

    st.markdown("---")

    # 종목 카드 렌더링
    for idx, row in filtered_df.iterrows():
        score = row['total_score']
        badge_class = "badge-score-high" if score >= 70 else "badge-score-mid"
        
        with st.container():
            st.markdown(f"""
            <div class="stock-card">
                <div class="stock-card-header">
                    <div>
                        <span class="stock-name">{row['name']}</span>
                        <span class="stock-code">({row['code']}) • {row['market']}</span>
                    </div>
                    <div class="{badge_class}">{score}점 [{row['grade']}]</div>
                </div>
                <div class="metric-grid">
                    <div class="metric-item">
                        <div class="metric-label">현재가</div>
                        <div class="metric-val" style="color:#EF4444;">{row['current_price']:,}원</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">52주 최저 이격률</div>
                        <div class="metric-val">+{row['diff_from_52w_low_pct']:.1f}%</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">외인 3일 순매수</div>
                        <div class="metric-val" style="color:#10B981;">{row['foreign_buy_3d']:+,}주</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">기관 3일 순매수</div>
                        <div class="metric-val" style="color:#10B981;">{row['organ_buy_3d']:+,}주</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 세부 펼치기 (차트 및 사유)
            with st.expander(f"🔍 **{row['name']}** 상세 분석 & 차트 열기", expanded=False):
                st.markdown("##### 💡 포착 사유 & 반등 근거")
                for reason in row['reasons']:
                    st.markdown(f"- {reason}")

                st.markdown("##### 📊 수급 및 가치 지표")
                pbr_str = f"{row['pbr']:.2f}배" if pd.notnull(row['pbr']) else "-"
                per_str = f"{row['per']:.1f}배" if pd.notnull(row['per']) else "-"
                st.markdown(f"- **PBR**: `{pbr_str}` | **PER**: `{per_str}`")
                st.markdown(f"- **거래량 급증률**: `{row['vol_surge_ratio']:.2f}배` | **RSI(14)**: `{row['rsi']:.1f}`")

                # 카카오톡 알림 보내기 버튼 & 네이버 증권 모바일 연결 버튼
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button(f"💬 카톡전송", key=f"k_btn_{row['code']}", use_container_width=True):
                        ok = send_kakao_stock_alert(KAKAO_REST_API_KEY, row.to_dict())
                        if ok:
                            st.toast(f"✅ {row['name']} 카카오톡 알림 발송 완료!", icon="💬")
                        else:
                            st.toast("⚠️ 카카오톡 메시지 전송 확인 필요", icon="⚠️")
                with btn_col2:
                    naver_mobile_url = f"https://m.stock.naver.com/item/main.naver?code={row['code']}"
                    st.markdown(f'<a href="{naver_mobile_url}" target="_blank" class="naver-btn" style="margin-top:0; padding:6px 10px; font-size:0.85rem;">네이버증권 ↗</a>', unsafe_allow_html=True)

                # Plotly 차트
                df_chart = fetch_stock_ohlcv(row['code'], days=90)
                if df_chart is not None and len(df_chart) > 0:
                    df_chart['MA5'] = df_chart['Close'].rolling(5).mean()
                    df_chart['MA20'] = df_chart['Close'].rolling(20).mean()
                    df_chart['RSI'] = calculate_rsi(df_chart['Close'], 14)
                    upper, mid, lower, _ = calculate_bollinger_bands(df_chart['Close'], 20, 2.0)
                    df_chart['BB_Upper'] = upper
                    df_chart['BB_Lower'] = lower

                    fig = make_subplots(
                        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=(f"{row['name']} 일봉 차트", "RSI (14)"),
                        row_heights=[0.7, 0.3]
                    )
                    fig.add_trace(go.Candlestick(
                        x=df_chart.index, open=df_chart['Open'], high=df_chart['High'],
                        low=df_chart['Low'], close=df_chart['Close'], name="주가",
                        increasing_line_color='#EF4444', decreasing_line_color='#3B82F6'
                    ), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA5'], name="5일선", line=dict(color='orange', width=1)), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA20'], name="20일선", line=dict(color='green', width=1.5)), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_Lower'], name="BB 하단", line=dict(color='red', dash='dash')), row=1, col=1)

                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['RSI'], name="RSI", line=dict(color='#8B5CF6')), row=2, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="red", row=2, col=1)

                    fig.update_layout(
                        height=420, margin=dict(l=10, r=10, t=30, b=10),
                        showlegend=False, xaxis_rangeslider_visible=False
                    )
                    st.plotly_chart(fig, use_container_width=True)

    # CSV 다운로드
    csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 검색 결과 CSV 다운로드",
        data=csv_data,
        file_name=f"바닥_반등_모바일_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True
    )
else:
    if not start_scan:
        st.info("👈 상단의 **[🚀 바닥 반등 종목 스캔 시작]** 버튼을 눌러주세요.")

        # PWA 안내 카드
        st.markdown("""
        <div style="background-color:#EFF6FF; border:1px solid #BFDBFE; padding:12px; border-radius:10px; margin-top:15px;">
            <h4 style="margin:0 0 8px 0; color:#1D4ED8;">📱 스마트폰 홈 화면에 앱으로 추가하는 방법</h4>
            <ol style="margin:0; padding-left:20px; font-size:0.85rem; color:#1E40AF;">
                <li><b>Android (Chrome)</b>: 브라우저 우측 상단 <b>[⋮] 메뉴</b> → <b>[홈 화면에 추가]</b> 선택</li>
                <li><b>iPhone (Safari)</b>: 하단 <b>[공유] 버튼</b> → <b>[홈 화면에 추가]</b> 선택</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
