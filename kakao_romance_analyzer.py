import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime

# -----------------------------------------------------------------------------
# 페이지 설정 & 커스텀 카카오 브랜딩 스타일링
# -----------------------------------------------------------------------------
try:
    st.set_page_config(
        page_title="💘 카톡 썸&연애 호감도 분석기",
        page_icon="💬",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
except Exception:
    pass

st.markdown("""
<style>
    .stApp {
        background-color: #FDFBF7;
    }
    .kakao-header {
        background: linear-gradient(135deg, #FEE500 0%, #FFD600 100%);
        padding: 20px;
        border-radius: 16px;
        color: #3C1E1E;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(254, 229, 0, 0.4);
    }
    .kakao-title {
        font-size: 1.6rem;
        font-weight: 900;
        margin: 0;
        color: #3C1E1E;
    }
    .kakao-sub {
        font-size: 0.95rem;
        color: #543A21;
        margin-top: 6px;
        font-weight: 600;
    }
    .score-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 20px;
        border: 2px solid #FEE500;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 15px;
    }
    .score-value {
        font-size: 3rem;
        font-weight: 900;
        color: #E11D48;
    }
    .metric-box {
        background-color: #FFFFFF;
        padding: 12px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        text-align: center;
        margin-bottom: 10px;
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 카카오톡 대화 파싱 함수
# -----------------------------------------------------------------------------
def parse_kakaotalk_chat(text: str) -> pd.DataFrame:
    records = []
    lines = text.strip().split('\n')
    
    # 1. PC 카카오톡 형식: [홍길동] [오후 11:15] 메시지
    pattern_pc = r'\[([^\]]+)\]\s*\[([^\]]+)\]\s*(.*)'
    # 2. 모바일 카카오톡 내보내기 형식: 2026. 10. 8. 23:15, 홍길동 : 메시지
    pattern_mobile = r'\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*(\d{1,2}:\d{2}),\s*([^:]+)\s*:\s*(.*)'
    # 3. 간편 형식: 홍길동: 메시지
    pattern_simple = r'^([^:]+)\s*:\s*(.*)'
    
    current_date = "2026-10-08"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 날짜 구분선 감지
        date_match = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', line)
        if date_match:
            y, m, d = date_match.groups()
            current_date = f"{y}-{int(m):02d}-{int(d):02d}"
            continue

        m_pc = re.match(pattern_pc, line)
        if m_pc:
            sender, time_str, msg = m_pc.groups()
            hour = 12
            if "오전" in time_str:
                h = int(re.search(r'\d+', time_str).group()) if re.search(r'\d+', time_str) else 9
                hour = 0 if h == 12 else h
            elif "오후" in time_str:
                h = int(re.search(r'\d+', time_str).group()) if re.search(r'\d+', time_str) else 1
                hour = 12 if h == 12 else h + 12
            
            records.append({
                "sender": sender.strip(),
                "time_str": time_str.strip(),
                "hour": hour,
                "message": msg.strip(),
                "char_len": len(msg.strip())
            })
            continue

        m_mb = re.match(pattern_mobile, line)
        if m_mb:
            time_str, sender, msg = m_mb.groups()
            h = int(time_str.split(':')[0]) if ':' in time_str else 12
            records.append({
                "sender": sender.strip(),
                "time_str": time_str.strip(),
                "hour": h,
                "message": msg.strip(),
                "char_len": len(msg.strip())
            })
            continue

        m_sp = re.match(pattern_simple, line)
        if m_sp and not line.startswith("http"):
            sender, msg = m_sp.groups()
            records.append({
                "sender": sender.strip(),
                "time_str": "12:00",
                "hour": 12,
                "message": msg.strip(),
                "char_len": len(msg.strip())
            })
            continue

    df = pd.DataFrame(records)
    return df

# -----------------------------------------------------------------------------
# 호감도 분석 엔진 (3인 이상 단톡방 1:1 두 사람 선택 지정 지원)
# -----------------------------------------------------------------------------
def analyze_romance_affection(df: pd.DataFrame, target_s1: str = None, target_s2: str = None):
    if df.empty:
        return None

    senders = list(df['sender'].unique())
    if len(senders) < 2:
        return None

    # 지정 대상 세팅
    s1 = target_s1 if target_s1 and target_s1 in senders else senders[0]
    s2 = target_s2 if target_s2 and target_s2 in senders else (senders[1] if len(senders) > 1 else senders[0])

    if s1 == s2:
        for s in senders:
            if s != s1:
                s2 = s
                break

    df1 = df[df['sender'] == s1]
    df2 = df[df['sender'] == s2]
    
    cnt1, cnt2 = len(df1), len(df2)
    pair_total = max(1, cnt1 + cnt2)
    pct1 = round((cnt1 / pair_total) * 100, 1)
    pct2 = round((cnt2 / pair_total) * 100, 1)
    
    avg_len1 = round(df1['char_len'].mean(), 1) if not df1.empty else 0
    avg_len2 = round(df2['char_len'].mean(), 1) if not df2.empty else 0
    
    q1 = df1['message'].str.contains(r'\?|궁금|뭐해|어때|어디').sum()
    q2 = df2['message'].str.contains(r'\?|궁금|뭐해|어때|어디').sum()
    q_pct1 = round((q1 / max(1, cnt1)) * 100, 1)
    q_pct2 = round((q2 / max(1, cnt2)) * 100, 1)
    
    lol1 = df1['message'].str.contains(r'ㅋ|ㅎ').sum()
    lol2 = df2['message'].str.contains(r'ㅋ|ㅎ').sum()
    
    heart_pattern = r'❤️|💕|😍|🥰|😘|🤍|💖|💗|💓|이모티콘'
    h1 = df1['message'].str.contains(heart_pattern).sum()
    h2 = df2['message'].str.contains(heart_pattern).sum()
    
    night1 = df1['hour'].apply(lambda x: 1 if (x >= 22 or x <= 2) else 0).sum()
    night2 = df2['hour'].apply(lambda x: 1 if (x >= 22 or x <= 2) else 0).sum()
    
    romantic_pattern = r'밥|맛있는|영화|카페|주말|만나|보고\s*싶|좋아|귀여|예쁘|멋지|잘\s*자'
    r1 = df1['message'].str.contains(romantic_pattern).sum()
    r2 = df2['message'].str.contains(romantic_pattern).sum()
    
    def calc_score(cnt, pct, avg_len, q_pct, hearts, romantic_cnt, night_cnt):
        sc = 0
        if 40 <= pct <= 60: sc += 20
        elif 30 <= pct <= 70: sc += 15
        else: sc += 10
        
        if avg_len >= 15: sc += 15
        elif avg_len >= 10: sc += 10
        else: sc += 5
        
        if q_pct >= 20: sc += 20
        elif q_pct >= 10: sc += 15
        else: sc += 8
        
        if hearts >= 5: sc += 20
        elif hearts >= 2: sc += 15
        else: sc += 8
        
        if romantic_cnt >= 5: sc += 15
        elif romantic_cnt >= 2: sc += 10
        else: sc += 5
        
        if night_cnt >= 3: sc += 10
        else: sc += 5
        
        return min(100, sc)

    score1 = calc_score(cnt1, pct1, avg_len1, q_pct1, h1, r1, night1)
    score2 = calc_score(cnt2, pct2, avg_len2, q_pct2, h2, r2, night2)
    mutual_score = round((score1 + score2) / 2)

    if mutual_score >= 88:
        status_text = "💘 서로 100% 그린라이트! 오늘 바로 고백각"
        status_color = "#DCFCE7"
        status_desc = f"{s1}님과 {s2}님의 대화는 서로에 대한 애정과 관심이 넘쳐납니다. 완벽한 그린라이트입니다!"
    elif mutual_score >= 75:
        status_text = "💞 호감 충만! 연애 발전 가능성 85%"
        status_color = "#E0F2FE"
        status_desc = f"두 분 사이의 호감이 뚜렷하며 긍정적인 신호가 자주 포착됩니다. 주말 데이트 약속을 잡아보세요!"
    elif mutual_score >= 60:
        status_text = "👀 은근한 썸 단계! 살짝 더 직진해볼 타이밍"
        status_color = "#FEF9C3"
        status_desc = f"서로 호감은 있으나 아직 조심스러운 단계입니다. 먼저 가벼운 데이트나 약속을 제안해 보세요."
    elif mutual_score >= 45:
        status_text = "💬 편한 친구 이상 썸 이하! 밀당이 필요한 단계"
        status_color = "#F3E8FF"
        status_desc = "대화는 이어지고 있으나 자발적인 호감 표현이나 질문 빈도를 좀 더 늘려볼 필요가 있습니다."
    else:
        status_text = "🧊 아직은 어색한 사이! 공통 관심사 탐색 필요"
        status_color = "#F1F5F9"
        status_desc = "대화 반응이 다소 아쉽습니다. 부담스럽지 않은 관심사 위주로 대화를 이끌어 보세요."

    return {
        "senders": senders,
        "s1": s1, "s2": s2,
        "cnt1": cnt1, "cnt2": cnt2,
        "pct1": pct1, "pct2": pct2,
        "avg_len1": avg_len1, "avg_len2": avg_len2,
        "q1": q1, "q2": q2,
        "q_pct1": q_pct1, "q_pct2": q_pct2,
        "h1": h1, "h2": h2,
        "r1": r1, "r2": r2,
        "night1": night1, "night2": night2,
        "score1": score1, "score2": score2,
        "mutual_score": mutual_score,
        "status_text": status_text,
        "status_color": status_color,
        "status_desc": status_desc
    }

# -----------------------------------------------------------------------------
# 샘플 대화 데이터셋
# -----------------------------------------------------------------------------
SAMPLE_FLIRT_CHAT = """[민우] [오후 10:15] 지은아 오늘 고생 많았어 ㅋㅋㅋ
[지은] [오후 10:16] 민우씨도 고생하셨어요!! 💕
[민우] [오후 10:17] 아까 회의 때 발표 너무 잘해서 멋있었어 진짜!
[지은] [오후 10:18] 히히 진짜요? 엄청 떨렸는데 다행이다 ㅠㅠ 고마워요!!
[민우] [오후 10:20] 이번 주말에 뭐해? 시간 괜찮으면 맛있는 거 먹으러 갈래?
[지은] [오후 10:21] 오 좋아요!! 주말에 특별한 일정 없는데 뭐 먹을까요? 😍
[민우] [오후 10:23] 지은이 파스타 좋아하잖아! 분위기 좋은 곳 찾아놨어 ㅋㅋㅋ
[지은] [오후 10:25] 대박... 저 완전 파스타 좋아해요!! 기대된다 헤헤
[민우] [오후 10:26] 그럼 토요일 1시에 보자! 잘 자고 내일 봐 지은아 ❤️
[지은] [오후 10:27] 네!! 민우씨도 잘 자요 굿밤! 💕"""

SAMPLE_FRIEND_CHAT = """[철수] [오후 2:10] 야 과제 다 했냐
[영희] [오후 2:15] 아니 아직 ㅋㅋㅋ 너는 함?
[철수] [오후 2:16] 나도 안 함 ㅋㅋㅋ 제출 언제까지냐
[영희] [오후 2:20] 오늘 밤 11시 59분까지임 얼른 해라
[철수] [오후 2:22] ㅇㅋ 고맙다"""

SAMPLE_GROUP_CHAT = """[민우] [오후 7:00] 얘들아 오늘 저녁 뭐 먹을까?
[지은] [오후 7:01] 나 파스타 먹고 싶어!! 💕
[수현] [오후 7:02] 난 삼겹살 고고
[민우] [오후 7:03] 지은이가 파스타 먹고 싶다니까 파스타 먹으러 가자 ㅋㅋㅋ
[지은] [오후 7:05] 대박 민우 최고!! 😍
[수현] [오후 7:06] 아 뭐냐 둘이 ㅋㅋㅋ 나 빠져야 됨?
[민우] [오후 7:08] 수현이 너도 같이 가야지 ㅋㅋㅋ 주말에 다 같이 보자!"""

def render_kakao_romance_app():
    st.markdown("""
    <div class="kakao-header">
        <div class="kakao-title">💘 카톡 썸&연애 호감도 분석기</div>
        <div class="kakao-sub">카카오톡 대화 내용으로 알아보는 1:1 및 다자간 호감도 지수</div>
    </div>
    """, unsafe_allow_html=True)

    # 입력 모드 선택 & 파일/텍스트 입력
    st.markdown("##### 📝 카카오톡 대화 내용 입력")

    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
    with btn_col1:
        if st.button("🔥 1:1 썸 대화", use_container_width=True):
            st.session_state.chat_input = SAMPLE_FLIRT_CHAT
    with btn_col2:
        if st.button("💬 1:1 친구 대화", use_container_width=True):
            st.session_state.chat_input = SAMPLE_FRIEND_CHAT
    with btn_col3:
        if st.button("👥 3인+ 단톡방 대화", use_container_width=True):
            st.session_state.chat_input = SAMPLE_GROUP_CHAT
    with btn_col4:
        if st.button("🧹 입력창 비우기", use_container_width=True):
            st.session_state.chat_input = ""

    if "chat_input" not in st.session_state:
        st.session_state.chat_input = SAMPLE_FLIRT_CHAT

    uploaded_file = st.file_uploader("📂 카카오톡 대화 내보내기 텍스트 파일(.txt) 업로드", type=["txt"])
    if uploaded_file is not None:
        try:
            raw_text = uploaded_file.read().decode("utf-8")
            st.session_state.chat_input = raw_text
            st.success("✅ 파일 업로드 완료!")
        except Exception:
            st.error("❌ 파일 읽기 실패. utf-8 인코딩 텍스트 파일인지 확인해 주세요.")

    chat_text = st.text_area(
        "카카오톡 대화 내용 (PC 복사본 또는 텍스트 내보내기)",
        value=st.session_state.chat_input,
        height=180,
        help="카카오톡 대화 내용을 복사해서 붙여넣으세요. 2명 및 3명 이상 단톡방도 지원합니다."
    )

    df_chat = parse_kakaotalk_chat(chat_text) if chat_text.strip() else pd.DataFrame()

    if not df_chat.empty:
        senders = list(df_chat['sender'].unique())
        if len(senders) >= 2:
            st.markdown("---")
            if len(senders) > 2:
                st.info(f"👥 **총 {len(senders)}명의 대화 참여자가 감지되었습니다!** ({', '.join(senders)})\n\n호감도를 분석할 두 대상을 지정하세요.")
            
            sel_col1, sel_col2 = st.columns(2)
            with sel_col1:
                target_s1 = st.selectbox("👤 분석 대상 1 (나 또는 상대방)", senders, index=0, key="target_s1_sel")
            with sel_col2:
                default_idx2 = 1 if len(senders) > 1 else 0
                target_s2 = st.selectbox("👤 분석 대상 2 (상대방 또는 나)", senders, index=default_idx2, key="target_s2_sel")

            if st.button("🚀 **선택한 대상 호감도 분석하기**", type="primary", use_container_width=True):
                if target_s1 == target_s2:
                    st.warning("⚠️ 서로 다른 두 사람을 선택해 주세요!")
                else:
                    res = analyze_romance_affection(df_chat, target_s1, target_s2)
                    if res:
                        st.session_state.analysis_result = res
                        st.session_state.df_chat = df_chat
                        st.toast(f"🎉 {target_s1} ❤️ {target_s2} 호감도 분석 완료!", icon="💘")
                    else:
                        st.error("❌ 분석 중 오류가 발생했습니다.")
        else:
            st.warning("⚠️ 2명 이상의 대화 참여자가 파싱되지 않았습니다. 대화 형식을 확인해 주세요.")

    # 분석 결과 리포트 렌더링
    if "analysis_result" in st.session_state and "df_chat" in st.session_state:
        res = st.session_state.analysis_result
        df_chat = st.session_state.df_chat
        
        st.markdown("---")
        
        # 1. 종합 호감도 점수 카드
        st.markdown(f"""
        <div class="score-card" style="background-color:{res['status_color']};">
            <div style="font-size:1.1rem; font-weight:800; color:#1E293B;">💘 [{res['s1']}] ❤️ [{res['s2']}] 1:1 호감도 지수</div>
            <div class="score-value">{res['mutual_score']}점</div>
            <div style="font-size:1.25rem; font-weight:800; color:#0F172A; margin-top:5px;">{res['status_text']}</div>
            <p style="font-size:0.9rem; color:#475569; margin-top:10px; line-height:1.5;">{res['status_desc']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 개별 호감도 비교
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            st.markdown(f"""
            <div class="metric-box">
                <div style="font-size:0.85rem; color:#64748B;"><b>{res['s1']}</b> ➡️ {res['s2']} 호감도</div>
                <div style="font-size:1.8rem; font-weight:800; color:#EC4899;">{res['score1']}점</div>
            </div>
            """, unsafe_allow_html=True)
        with s_col2:
            st.markdown(f"""
            <div class="metric-box">
                <div style="font-size:0.85rem; color:#64748B;"><b>{res['s2']}</b> ➡️ {res['s1']} 호감도</div>
                <div style="font-size:1.8rem; font-weight:800; color:#3B82F6;">{res['score2']}점</div>
            </div>
            """, unsafe_allow_html=True)

        # 탭 구성: 상세 분석
        tab_list = ["📊 대화 지분율 & 분석", "❤️ 애정 표현 & 이모티콘", "🌙 심야 대화 & 데이트 키워드"]
        if len(res['senders']) > 2:
            tab_list.append("👥 단톡방 전체 대화량 분석")
            
        tabs = st.tabs(tab_list)

        with tabs[0]:
            st.markdown(f"##### 💬 [{res['s1']}] vs [{res['s2']}] 대화량 및 질문 지분율")
            
            # 지분율 차트
            df_pie = pd.DataFrame({
                "sender": [res['s1'], res['s2']],
                "count": [res['cnt1'], res['cnt2']]
            })
            fig_pie = px.pie(df_pie, values='count', names='sender', title=f"두 사람 간 대화 지분율 (%)",
                             color_discrete_sequence=['#EC4899', '#3B82F6'], hole=0.4)
            fig_pie.update_layout(height=280, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)

            st.markdown(f"""
            - **{res['s1']}** 메시지 수: `{res['cnt1']}개` | 평균 글자수: `{res['avg_len1']}자` | 질문 비율: `{res['q_pct1']}%`
            - **{res['s2']}** 메시지 수: `{res['cnt2']}개` | 평균 글자수: `{res['avg_len2']}자` | 질문 비율: `{res['q_pct2']}%`
            """)

        with tabs[1]:
            st.markdown("##### ❤️ 하트/이모티콘 & ㅋ/ㅎ 빈도 비교")
            df_emo = pd.DataFrame({
                "이름": [res['s1'], res['s2']],
                "하트/이모티콘": [res['h1'], res['h2']],
                "ㅋ/ㅎ (웃음)": [df_chat[df_chat['sender']==res['s1']]['message'].str.contains(r'ㅋ|ㅎ').sum(),
                                 df_chat[df_chat['sender']==res['s2']]['message'].str.contains(r'ㅋ|ㅎ').sum()]
            })
            fig_bar = px.bar(df_emo, x='이름', y=['하트/이모티콘', 'ㅋ/ㅎ (웃음)'], barmode='group',
                             color_discrete_sequence=['#EC4899', '#FBBF24'], title="애정 및 반응 표출 횟수")
            fig_bar.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_bar, use_container_width=True)

        with tabs[2]:
            st.markdown("##### 🌙 심야 대화 & 데이트 약속 모멘텀")
            st.markdown(f"""
            - **밤 10시 ~ 새벽 2시 대화 건수**:
              - **{res['s1']}**: `{res['night1']}회`
              - **{res['s2']}**: `{res['night2']}회`
            - **데이트 / 약속 / 호감 키워드 포착 횟수**:
              - **{res['s1']}**: `{res['r1']}회`
              - **{res['s2']}**: `{res['r2']}회`
            """)
            if res['r1'] > 0 or res['r2'] > 0:
                st.success("🎉 대화 속에서 약속/데이트 관련 긍정 키워드가 포착되었습니다!")
            else:
                st.info("💡 주말 데이트나 맛집 이야기를 꺼내어 대화에 활력을 불어넣어 보세요.")

        if len(res['senders']) > 2 and len(tabs) > 3:
            with tabs[3]:
                st.markdown("##### 👥 단톡방 참여자 전체 대화 지분 순위")
                df_group = df_chat['sender'].value_counts().reset_index()
                df_group.columns = ['참여자', '메시지 수']
                fig_group = px.bar(df_group, x='참여자', y='메시지 수', color='메시지 수',
                                   color_continuous_scale='Viridis', title="전체 참여자 대화량 비교")
                fig_group.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig_group, use_container_width=True)

render_kakao_romance_app()
