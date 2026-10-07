import requests
import json
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

POSITIVE_TREND_KEYWORDS = {
    "AI/반도체": ["AI", "인공지능", "반도체", "HBM", "CXL", "엔비디아", "파운드리", "클라우드", "생성형"],
    "이차전지/배터리": ["이차전지", "배터리", "양극재", "음극재", "리튬", "전고체", "LFP"],
    "바이오/헬스케어": ["바이오", "FDA", "임상", "신약", "기술수출", "승인", "특허", "치매", "비만치료제"],
    "로봇/자율주행": ["로봇", "자율주행", "스마트팩토리", "협동로봇", "피규어"],
    "방산/우주항공": ["방산", "수주", "무기", "우주", "위성", "수출", "K방산", "천궁"],
    "원전/전력": ["원전", "SMR", "체코원전", "전력망", "변압기", "초고압"],
    "실적/어닝서프라이즈": ["실적", "흑자", "최대실적", "어닝서프라이즈", "영업이익", "매출최대", "사상최대"],
    "주주환원/밸류업": ["자사주", "소각", "배당", "밸류업", "주주환원", "공개매수"]
}

NEGATIVE_KEYWORDS = ["적자", "유상증자", "횡령", "배임", "소송", "과징금", "감자", "하향", "부도", "구속"]

def fetch_stock_trend_issues(code: str) -> dict:
    """
    네이버 실시간 뉴스 API를 조치하여 최신 이슈/트렌드 테마 및 호재/악재 감성 분석
    """
    url = f"https://m.stock.naver.com/api/news/stock/{code}?pageSize=8"
    trend_score = 0
    matched_themes = set()
    pos_reasons = []
    neg_reasons = []
    recent_news = []

    try:
        res = requests.get(url, headers=HEADERS, timeout=3)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list):
                for entry in data:
                    items = entry.get("items", [])
                    for item in items:
                        title = item.get("titleFull", "") or item.get("title", "")
                        body = item.get("body", "")
                        link = item.get("mobileNewsUrl", "")
                        full_text = f"{title} {body}"

                        if title and len(recent_news) < 3:
                            recent_news.append({
                                "title": title,
                                "url": link if link else f"https://m.stock.naver.com/item/main.naver?code={code}"
                            })

                        # 1. 긍정 트렌드 테마 감지
                        for theme, keywords in POSITIVE_TREND_KEYWORDS.items():
                            for kw in keywords:
                                if kw in full_text and theme not in matched_themes:
                                    matched_themes.add(theme)
                                    trend_score += 4
                                    pos_reasons.append(f"🔥 최신 이슈/트렌드: [{theme}] ({kw} 관련 호재 포착)")
                                    break

                        # 2. 악재 감지
                        for neg_kw in NEGATIVE_KEYWORDS:
                            if neg_kw in title:
                                trend_score -= 5
                                neg_reasons.append(f"⚠️ 리스크 이슈: {neg_kw} 관련 악재 보도 포착")
                                break
    except Exception as e:
        pass

    # 점수 범위 제한 (-10 ~ +15점)
    final_trend_score = max(-10, min(15, trend_score))

    return {
        "trend_score": final_trend_score,
        "matched_themes": list(matched_themes),
        "pos_reasons": pos_reasons[:3],
        "neg_reasons": neg_reasons[:2],
        "recent_news": recent_news[:3]
    }
