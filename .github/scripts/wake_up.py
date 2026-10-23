import time
from playwright.sync_api import sync_playwright

URLS = [
    "https://realoshstock2.streamlit.app",
    "https://kakao-romance.streamlit.app"
]

def wake_up_apps():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for url in URLS:
            try:
                print(f"[*] Navigating to {url}...")
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(5)
                
                # Check for sleep indicators and button
                content = page.content()
                print(f"[*] Page title: {page.title()}, Content length: {len(content)}")
                
                # Try finding button by text
                selectors = [
                    "button:has-text('Yes, get this app back up')",
                    "button:has-text('get this app back up')",
                    "button:has-text('Wake up')",
                    "button:has-text('wake up')",
                    "[data-testid='stAppSleepWakeUpButton']"
                ]
                
                clicked = False
                for sel in selectors:
                    btn = page.locator(sel)
                    if btn.count() > 0:
                        print(f"[!] Found wake-up button using selector '{sel}'. Clicking...")
                        btn.first.click()
                        time.sleep(15)
                        clicked = True
                        print("[+] Clicked successfully and waited 15s!")
                        break
                
                if not clicked:
                    print(f"[OK] No wake-up button found on {url} (App is likely awake or waking up).")
                page.close()
            except Exception as e:
                print(f"[!] Error checking {url}: {e}")
        browser.close()

if __name__ == "__main__":
    wake_up_apps()
