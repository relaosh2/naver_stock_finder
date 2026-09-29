import requests
import json

def send_telegram_stock_alert(bot_token: str, chat_id: str, stock: dict) -> bool:
    """
    텔레그램 봇 API를 이용하여 반등 종목 알림 전송 (토큰 만료 없음, 100% 무료)
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    code = stock['code']
    name = stock['name']
    score = stock['total_score']
    price = stock['current_price']
    diff_low = stock['diff_from_52w_low_pct']
    f_buy = stock['foreign_buy_3d']
    o_buy = stock['organ_buy_3d']
    grade = stock['grade']
    reasons = "\n• ".join(stock['reasons'][:3])

    text = f"""📈 <b>[갓성호님의 바닥에서 난 잡아] 반등 신호 포착!</b>

📌 <b>{name}</b> ({code})
• <b>반등점수</b>: {score}점 [{grade}]
• <b>현재가</b>: {price:,}원 (52주최저 대비 +{diff_low:.1f}%)
• <b>외인 3일</b>: {f_buy:+,}주 | <b>기관</b>: {o_buy:+,}주

💡 <b>포착사유:</b>
• {reasons}

📱 <a href="https://realosh-stock.streamlit.app">모바일 앱에서 차트 보기 ↗</a>
"""

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            print(f"✅ 텔레그램 [{name}] 알림 전송 성공!")
            return True
        else:
            print(f"❌ 텔레그램 전송 실패: {res.text}")
            return False
    except Exception as e:
        print(f"❌ 텔레그램 API 에러: {e}")
        return False
