import sys
import time
import schedule
from datetime import datetime
from kakao_notifier import send_kakao_stock_alert, KAKAO_REST_API_KEY
from scanner import run_stock_scan

# 오늘 이미 알림을 보낸 종목 코드 저장 (중복 발송 방지)
alerted_today = set()

def job_scan_and_alert_9am():
    now = datetime.now()
    # 주말(토, 일) 제외 (월: 0 ~ 금: 4)
    if now.weekday() >= 5:
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] ☕ 오늘은 주말입니다. 스캔을 건너뜁니다.")
        return

    print("=" * 65)
    print(f"⏰ [{now.strftime('%Y-%m-%d %H:%M:%S')}] 갓성호님의 9시 정기 바닥 반등 종목 자동 스캔 시작!")
    print("=" * 65)

    try:
        # 시총 상위 150개 종목 대상 반등 스캔
        df_res = run_stock_scan(market="ALL", top_n=150)
        
        if df_res is None or df_res.empty:
            print("발굴된 반등 종목이 없습니다.")
            return

        # 반등 점수 60점 이상 유망 종목 필터링
        target_stocks = df_res[df_res['total_score'] >= 60].to_dict('records')
        print(f"🎯 총 {len(target_stocks)}개 반등 유망 종목 포착완료!")

        sent_cnt = 0
        for stock in target_stocks:
            code = stock['code']
            if code not in alerted_today:
                success = send_kakao_stock_alert(KAKAO_REST_API_KEY, stock)
                if success:
                    alerted_today.add(code)
                    sent_cnt += 1
                    time.sleep(1.5) # 카카오 API 도배 방지 간격

        print("=" * 65)
        print(f"✅ [{now.strftime('%H:%M:%S')}] 총 {sent_cnt}건의 바닥 반등 종목 카카오톡 메시지 발송 완료!")
        print("=" * 65 + "\n")

    except Exception as e:
        print(f"❌ 9시 스캔/발송 도중 에러 발생: {e}")


def start_9am_scheduler():
    print("=" * 65)
    print(" ⏰ 갓성호님의 매일 아침 9:00 카카오톡 바닥반등 종목 자동 알림 스케줄러 가동중...")
    print(" 💡 매일 아침 09:00 정각에 주시장을 스캔하여 카카오톡으로 자동 발송합니다.")
    print(" 💡 본 창을 켜두시면 매일 아침 9시에 자동으로 알림 메시지가 발송됩니다.")
    print("=" * 65 + "\n")

    # 매일 아침 09:00 에 자동 실행 등록
    schedule.every().day.at("09:00").do(job_scan_and_alert_9am)

    # 명령인자로 --now 전달 시 즉시 1회 테스트 실행
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        print("⚡ 즉시 스캔 및 카카오톡 전송 테스트를 진행합니다...")
        job_scan_and_alert_9am()

    # 무한 루프 대기
    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    start_9am_scheduler()
