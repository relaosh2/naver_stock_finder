import socket
import qrcode
import sys
import io

# Windows 인코딩 처리
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def show_qr():
    local_ip = get_local_ip()
    mobile_url = f"http://{local_ip}:5000"

    print("=" * 60)
    print(" [모바일 앱 접속 안내] 네이버 증권 바닥 반등 주식찾기")
    print("=" * 60)
    print(f"\n [스마트폰 브라우저 직접 입력]: {mobile_url}\n")
    print(" [스마트폰 카메라 QR코드 스캔 접속]:")

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=1,
    )
    qr.add_data(mobile_url)
    qr.make(fit=True)

    try:
        qr.print_ascii(invert=True)
    except Exception:
        qr.print_tty()

    print("\n" + "=" * 60)
    print(" [스마트폰 모바일 앱 접속 방법]:")
    print(f" 1. 스마트폰(Android/iPhone)을 동일한 Wi-Fi에 연결합니다.")
    print(f" 2. 카메라인식으로 위 QR 코드를 찍어 {mobile_url} 로 접속합니다.")
    print(" 3. 스마트폰 브라우저 메뉴에서 [홈 화면에 추가]를 누르면 앱으로 추가됩니다.")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    show_qr()
