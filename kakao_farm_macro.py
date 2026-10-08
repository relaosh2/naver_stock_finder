import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import random
import sys
import os

# Attempt importing required dependencies
try:
    import pyautogui
    pyautogui.FAILSAFE = True
except ImportError:
    pyautogui = None

try:
    import keyboard
except ImportError:
    keyboard = None


class KakaoFarmMacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("카카오톡 [무한의 농장] 통합 매크로 v1.1")
        self.root.geometry("500x620")
        self.root.resizable(False, False)

        # Macro State
        self.is_running = False
        self.active_mode = "clicker" # "clicker", "drag", "image"
        self.macro_thread = None

        # Variables - Clicker Mode
        self.click_target_x = tk.IntVar(value=500)
        self.click_target_y = tk.IntVar(value=500)
        self.click_interval_ms = tk.IntVar(value=100)
        self.random_jitter = tk.BooleanVar(value=True)
        self.click_type = tk.StringVar(value="fixed") # "fixed", "current", "area"

        # Area Bounds
        self.area_x1 = tk.IntVar(value=400)
        self.area_y1 = tk.IntVar(value=300)
        self.area_x2 = tk.IntVar(value=600)
        self.area_y2 = tk.IntVar(value=700)

        # Variables - Drag / Merge Mode
        self.drag_start_x = tk.IntVar(value=400)
        self.drag_start_y = tk.IntVar(value=400)
        self.drag_end_x = tk.IntVar(value=500)
        self.drag_end_y = tk.IntVar(value=500)
        self.drag_duration_ms = tk.IntVar(value=200)
        self.drag_repeat_interval = tk.IntVar(value=500)

        self._build_ui()
        self._setup_hotkeys()

    def _setup_hotkeys(self):
        if keyboard:
            try:
                keyboard.add_hotkey('f8', self.toggle_macro)
                keyboard.add_hotkey('f9', self.stop_macro)
            except Exception as e:
                print(f"핫키 등록 경고: {e}")

    def _build_ui(self):
        # Top Header
        header_frame = ttk.Frame(self.root, padding=10)
        header_frame.pack(fill=tk.X)

        title_label = ttk.Label(
            header_frame, 
            text="🌾 카카오톡 무한의 농장 자동 매크로 🌾", 
            font=("Malgun Gothic", 15, "bold"),
            foreground="#2C3E50"
        )
        title_label.pack(anchor=tk.CENTER)

        sub_label = ttk.Label(
            header_frame, 
            text="단축키: [F8] 시작/일시정지 | [F9] 중지 | 화면 구석으로 마우스 이동 시 긴급정지", 
            font=("Malgun Gothic", 9),
            foreground="#7F8C8D"
        )
        sub_label.pack(anchor=tk.CENTER, pady=(3, 0))

        # Status Bar
        self.status_frame = tk.Frame(self.root, bg="#E74C3C", height=38)
        self.status_frame.pack(fill=tk.X, padx=12, pady=5)
        self.status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            self.status_frame, 
            text="● 매크로 정지됨 (F8을 눌러 시작)", 
            fg="white", 
            bg="#E74C3C",
            font=("Malgun Gothic", 10, "bold")
        )
        self.status_label.pack(expand=True)

        # Tabs Setup
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # Tab 1: Clicker Mode
        tab_clicker = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_clicker, text=" ⚡ 고속 연타 / 파밍 ")
        self._build_clicker_tab(tab_clicker)

        # Tab 2: Drag & Merge Mode
        tab_drag = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_drag, text=" 🔄 드래그 / 합성 ")
        self._build_drag_tab(tab_drag)

        # Tab 3: Guide & TOS
        tab_guide = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_guide, text=" ℹ️ 사용 방법 및 팁 ")
        self._build_guide_tab(tab_guide)

        # Global Control Buttons
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill=tk.X)

        self.btn_start = tk.Button(
            btn_frame, 
            text="▶ 매크로 시작 (F8)", 
            bg="#2ECC71", 
            fg="white", 
            font=("Malgun Gothic", 11, "bold"),
            height=2,
            command=self.start_macro
        )
        self.btn_start.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        self.btn_stop = tk.Button(
            btn_frame, 
            text="⏹ 매크로 중지 (F9)", 
            bg="#E74C3C", 
            fg="white", 
            font=("Malgun Gothic", 11, "bold"),
            height=2,
            command=self.stop_macro
        )
        self.btn_stop.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=4)

    def _build_clicker_tab(self, parent):
        # Click Type Group
        group_type = ttk.LabelFrame(parent, text=" 클릭 대상 설정 ", padding=10)
        group_type.pack(fill=tk.X, pady=5)

        ttk.Radiobutton(group_type, text="특정 지정 좌표 연타", variable=self.click_type, value="fixed", command=self._update_click_ui).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(group_type, text="현재 마우스 포인터 위치 연타", variable=self.click_type, value="current", command=self._update_click_ui).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(group_type, text="농장 밭 사각형 영역 난수 연타 (자동 수확/터치)", variable=self.click_type, value="area", command=self._update_click_ui).pack(anchor=tk.W, pady=2)

        # Fixed Coordinate Frame
        self.fixed_frame = ttk.Frame(group_type)
        self.fixed_frame.pack(fill=tk.X, pady=5)

        ttk.Label(self.fixed_frame, text="X 좌표:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(self.fixed_frame, textvariable=self.click_target_x, width=6).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(self.fixed_frame, text="Y 좌표:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(self.fixed_frame, textvariable=self.click_target_y, width=6).pack(side=tk.LEFT, padx=(0, 10))

        self.btn_pick_coord = ttk.Button(self.fixed_frame, text="🎯 3초 후 좌표 추출", command=self.pick_click_coord)
        self.btn_pick_coord.pack(side=tk.LEFT)

        # Area Coordinate Frame
        self.area_frame = ttk.Frame(group_type)
        self.area_frame.pack(fill=tk.X, pady=5)

        ttk.Label(self.area_frame, text="밭 영역 X1,Y1:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(self.area_frame, textvariable=self.area_x1, width=5).pack(side=tk.LEFT)
        ttk.Entry(self.area_frame, textvariable=self.area_y1, width=5).pack(side=tk.LEFT, padx=(2, 8))

        ttk.Label(self.area_frame, text="~ X2,Y2:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(self.area_frame, textvariable=self.area_x2, width=5).pack(side=tk.LEFT)
        ttk.Entry(self.area_frame, textvariable=self.area_y2, width=5).pack(side=tk.LEFT, padx=(2, 0))

        # Speed Options Frame
        group_opt = ttk.LabelFrame(parent, text=" 속도 및 자연스러운 터치 옵션 ", padding=10)
        group_opt.pack(fill=tk.X, pady=10)

        interval_row = ttk.Frame(group_opt)
        interval_row.pack(fill=tk.X, pady=5)
        ttk.Label(interval_row, text="클릭 간격 (밀리초):").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(interval_row, textvariable=self.click_interval_ms, width=8).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(interval_row, text="ms (100ms = 초당 10회 터치)").pack(side=tk.LEFT)

        chk_jitter = ttk.Checkbutton(
            group_opt, 
            text="사람 터치 흉내 (딜레이 ±15% 랜덤 및 위치 미세 흔듦)", 
            variable=self.random_jitter
        )
        chk_jitter.pack(anchor=tk.W, pady=5)

        self._update_click_ui()

    def _update_click_ui(self):
        mode = self.click_type.get()
        if mode == "fixed":
            self.fixed_frame.pack(fill=tk.X, pady=5)
            self.area_frame.pack_forget()
        elif mode == "area":
            self.fixed_frame.pack_forget()
            self.area_frame.pack(fill=tk.X, pady=5)
        else: # current
            self.fixed_frame.pack_forget()
            self.area_frame.pack_forget()

    def _build_drag_tab(self, parent):
        group_drag = ttk.LabelFrame(parent, text=" 농작물 드래그 / 자동 합성 ", padding=10)
        group_drag.pack(fill=tk.X, pady=5)

        ttk.Label(group_drag, text="시작 좌표 (X1, Y1):").grid(row=0, column=0, sticky=tk.W, pady=5)
        f_start = ttk.Frame(group_drag)
        f_start.grid(row=0, column=1, sticky=tk.W)
        ttk.Entry(f_start, textvariable=self.drag_start_x, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Entry(f_start, textvariable=self.drag_start_y, width=6).pack(side=tk.LEFT, padx=2)

        ttk.Label(group_drag, text="도착 좌표 (X2, Y2):").grid(row=1, column=0, sticky=tk.W, pady=5)
        f_end = ttk.Frame(group_drag)
        f_end.grid(row=1, column=1, sticky=tk.W)
        ttk.Entry(f_end, textvariable=self.drag_end_x, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Entry(f_end, textvariable=self.drag_end_y, width=6).pack(side=tk.LEFT, padx=2)

        ttk.Label(group_drag, text="드래그 속도 (ms):").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(group_drag, textvariable=self.drag_duration_ms, width=8).grid(row=2, column=1, sticky=tk.W)

        ttk.Label(group_drag, text="반복 간격 (ms):").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Entry(group_drag, textvariable=self.drag_repeat_interval, width=8).grid(row=3, column=1, sticky=tk.W)

        btn_pick_drag = ttk.Button(group_drag, text="🎯 시작/끝 좌표 연속 측정", command=self.pick_drag_coords)
        btn_pick_drag.grid(row=4, column=0, columnspan=2, pady=10)

    def _build_guide_tab(self, parent):
        txt = tk.Text(parent, wrap=tk.WORD, font=("Malgun Gothic", 9), height=18)
        txt.pack(fill=tk.BOTH, expand=True)

        guide_content = """📖 [무한의 농장] 매크로 사용 가이드

1. ⚡ 고속 연타 / 파밍 모드:
   - 카카오톡 내 [무한의 농장] 게임 화면의 밭(농작물 생성/수확 버튼) 위치에 마우스를 대고 [F8] 키를 누르면 자동 연타가 시작됩니다.
   - [지정 좌표 연타]: 특정 수확/합성 버튼 위치의 X, Y 좌표를 저장해두고 해당 위치만 빠른 속도로 연타합니다.
   - [영역 난수 연타]: 밭 전체 사각형 영역 좌표를 입력하면 해당 범위 내부를 무작위로 연타하여 농작물 심기 및 수확을 자동으로 수행합니다.

2. 🔄 드래그 / 합성 모드:
   - 동일한 레벨의 농작물을 합성하기 위해 특정 위치에서 다른 위치로 끌어다 놓는 드래그 동작을 자동 반복합니다.

3. 🛡️ 제재 방지 기능:
   - '사람 터치 흉내' 옵션을 켜두면 터치 간격과 좌표에 미세한 난수(Jitter)가 적용되어 단순 반복 클릭 탐지를 방지합니다.

4. 🚨 긴급 정지 기능:
   - 동작 중 언제든지 [F9] 키를 누르거나, 마우스 포인터를 화면 맨 모서리(왼쪽 위 등)로 빠르게 이동시키면 자동으로 매크로가 즉시 중단됩니다.
"""
        txt.insert(tk.END, guide_content)
        txt.config(state=tk.DISABLED)

    def pick_click_coord(self):
        def countdown():
            for i in range(3, 0, -1):
                self.btn_pick_coord.config(text=f"🎯 {i}초 뒤 위치 추출...")
                time.sleep(1)
            if pyautogui:
                x, y = pyautogui.position()
                self.click_target_x.set(x)
                self.click_target_y.set(y)
            self.btn_pick_coord.config(text="🎯 3초 후 좌표 추출")
            messagebox.showinfo("완료", f"저장된 좌표: X={self.click_target_x.get()}, Y={self.click_target_y.get()}")

        threading.Thread(target=countdown, daemon=True).start()

    def pick_drag_coords(self):
        def countdown():
            messagebox.showinfo("안내", "확인을 누르고 3초 뒤 [드래그 시작 위치]에 마우스를 올리세요.")
            time.sleep(3)
            if pyautogui:
                sx, sy = pyautogui.position()
                self.drag_start_x.set(sx)
                self.drag_start_y.set(sy)
            
            messagebox.showinfo("안내", f"시작점 (X={sx}, Y={sy}) 저장 완료!\n3초 뒤 [드래그 도착 위치]에 마우스를 올리세요.")
            time.sleep(3)
            if pyautogui:
                ex, ey = pyautogui.position()
                self.drag_end_x.set(ex)
                self.drag_end_y.set(ey)
            
            messagebox.showinfo("완료", f"드래그 설정 완료:\n시작({sx}, {sy}) ➔ 도착({ex}, {ey})")

        threading.Thread(target=countdown, daemon=True).start()

    def toggle_macro(self):
        if self.is_running:
            self.stop_macro()
        else:
            self.start_macro()

    def start_macro(self):
        if self.is_running:
            return

        if pyautogui is None:
            messagebox.showerror("오류", "pyautogui 라이브러리가 설치되지 않았습니다.")
            return

        self.is_running = True
        self.status_frame.config(bg="#2ECC71")
        self.status_label.config(text="● 매크로 동작 중... (F9 또는 ESC로 중지)", bg="#2ECC71")

        # Check current selected tab
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 0:
            target_func = self._run_clicker_loop
        elif selected_tab == 1:
            target_func = self._run_drag_loop
        else:
            target_func = self._run_clicker_loop

        self.macro_thread = threading.Thread(target=target_func, daemon=True)
        self.macro_thread.start()

    def stop_macro(self):
        if not self.is_running:
            return

        self.is_running = False
        self.status_frame.config(bg="#E74C3C")
        self.status_label.config(text="● 매크로 정지됨 (F8을 눌러 시작)", bg="#E74C3C")

    def _run_clicker_loop(self):
        pyautogui.PAUSE = 0.005

        while self.is_running:
            try:
                mode = self.click_type.get()
                interval = max(0.01, self.click_interval_ms.get() / 1000.0)

                if mode == "fixed":
                    cx = self.click_target_x.get()
                    cy = self.click_target_y.get()
                elif mode == "current":
                    cx, cy = pyautogui.position()
                elif mode == "area":
                    x1, y1 = self.area_x1.get(), self.area_y1.get()
                    x2, y2 = self.area_x2.get(), self.area_y2.get()
                    cx = random.randint(min(x1, x2), max(x1, x2))
                    cy = random.randint(min(y1, y2), max(y1, y2))

                if self.random_jitter.get() and mode != "area":
                    cx += random.randint(-2, 2)
                    cy += random.randint(-2, 2)
                    jitter_delay = random.uniform(-0.15 * interval, 0.15 * interval)
                    sleep_time = max(0.005, interval + jitter_delay)
                else:
                    sleep_time = interval

                pyautogui.click(x=cx, y=cy)
                time.sleep(sleep_time)

            except pyautogui.FailSafeException:
                print("긴급 정지 발생")
                self.root.after(0, self.stop_macro)
                break
            except Exception as e:
                print(f"클릭 루프 예외: {e}")
                time.sleep(0.2)

    def _run_drag_loop(self):
        pyautogui.PAUSE = 0.01

        while self.is_running:
            try:
                sx, sy = self.drag_start_x.get(), self.drag_start_y.get()
                ex, ey = self.drag_end_x.get(), self.drag_end_y.get()
                duration = max(0.05, self.drag_duration_ms.get() / 1000.0)
                repeat_delay = max(0.1, self.drag_repeat_interval.get() / 1000.0)

                if self.random_jitter.get():
                    sx += random.randint(-3, 3)
                    sy += random.randint(-3, 3)
                    ex += random.randint(-3, 3)
                    ey += random.randint(-3, 3)

                pyautogui.moveTo(sx, sy)
                pyautogui.dragTo(ex, ey, duration=duration, button='left')
                time.sleep(repeat_delay)

            except pyautogui.FailSafeException:
                print("긴급 정지 발생")
                self.root.after(0, self.stop_macro)
                break
            except Exception as e:
                print(f"드래그 루프 예외: {e}")
                time.sleep(0.5)


def main():
    root = tk.Tk()
    app = KakaoFarmMacroApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
