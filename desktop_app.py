import sys
import os
import threading
import tempfile
import webbrowser
from datetime import datetime
import pandas as pd
import numpy as np

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("System")  # Light/Dark
    ctk.set_default_color_theme("blue")
    USE_CTK = True
except ImportError:
    USE_CTK = False

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from scanner import run_stock_scan
from data_fetcher import fetch_stock_ohlcv
from technical_indicators import calculate_rsi, calculate_bollinger_bands

class StockFinderDesktopApp:
    def __init__(self):
        if USE_CTK:
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()
            
        self.root.title("📈 네이버 증권 바닥 반등 유망주 발굴기 (Desktop App)")
        self.root.geometry("1350x850")
        self.root.minsize(1050, 700)

        self.scan_data = None
        self.filtered_df = None
        self.selected_code = None

        self.setup_ui()

    def setup_ui(self):
        # 1. 메인 레이아웃 (헤더, 메인 스플리터)
        if USE_CTK:
            # 헤더
            header_frame = ctk.CTkFrame(self.root, fg_color=("white", "#1E293B"), corner_radius=8)
            header_frame.pack(fill="x", px=15, py=10, padx=15, pady=(10, 5))
            
            title_label = ctk.CTkLabel(
                header_frame, text="📊 네이버 증권 바닥권 반등 유망주 발굴기",
                font=ctk.CTkFont(family="Malgun Gothic", size=20, weight="bold"),
                text_color=("#1E3A8A", "#60A5FA")
            )
            title_label.pack(anchor="w", padx=15, pady=(10, 2))

            sub_label = ctk.CTkLabel(
                header_frame,
                text="52주 최저가/과매도 바닥 + 외인·기관 수급 유입 + 거래량 급증 + 저평가 밸류 종합 분석 시스템",
                font=ctk.CTkFont(family="Malgun Gothic", size=12),
                text_color=("#4B5563", "#9CA3AF")
            )
            sub_label.pack(anchor="w", padx=15, pady=(0, 10))

            # 메인 컨테이너
            main_container = ctk.CTkFrame(self.root, fg_color="transparent")
            main_container.pack(fill="both", expand=True, padx=15, pady=5)

            # [좌측 사이드바]
            sidebar = ctk.CTkScrollableFrame(main_container, width=320, label_text="🔍 스캔 조건 및 필터")
            sidebar.pack(side="left", fill="y", padx=(0, 10))

            # 대상 시장
            ctk.CTkLabel(sidebar, text="대상 시장 선택", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 2))
            self.market_var = ctk.StringVar(value="전체 (KOSPI + KOSDAQ)")
            self.combo_market = ctk.CTkOptionMenu(
                sidebar, values=["전체 (KOSPI + KOSDAQ)", "코스피 (KOSPI)", "코스닥 (KOSDAQ)"],
                variable=self.market_var
            )
            self.combo_market.pack(fill="x", pady=(0, 10))

            # 스캔 범위 슬라이더
            ctk.CTkLabel(sidebar, text="시가총액 상위 스캔 범위", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
            self.top_n_label = ctk.CTkLabel(sidebar, text="150개 종목", text_color="#3B82F6")
            self.top_n_label.pack(anchor="w")
            
            self.slider_top_n = ctk.CTkSlider(
                sidebar, from_=30, to=500, number_of_steps=47,
                command=lambda v: self.top_n_label.configure(text=f"{int(v)}개 종목")
            )
            self.slider_top_n.set(150)
            self.slider_top_n.pack(fill="x", pady=(0, 10))

            # 최소 점수 슬라이더
            ctk.CTkLabel(sidebar, text="최소 반등 점수 (Score)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 2))
            self.score_label = ctk.CTkLabel(sidebar, text="45점 이상", text_color="#3B82F6")
            self.score_label.pack(anchor="w")
            
            self.slider_min_score = ctk.CTkSlider(
                sidebar, from_=35, to=85, number_of_steps=10,
                command=lambda v: self.on_score_slider_change(v)
            )
            self.slider_min_score.set(45)
            self.slider_min_score.pack(fill="x", pady=(0, 10))

            # 프리셋 그룹
            grp_preset = ctk.CTkFrame(sidebar)
            grp_preset.pack(fill="x", pady=10, ipadx=5, ipady=5)
            ctk.CTkLabel(grp_preset, text="⚡ 전략별 1-Click 프리셋", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
            
            btn_p1 = ctk.CTkButton(grp_preset, text="🔥 외인+기관 쌍끌이 바닥주", fg_color="#F59E0B", hover_color="#D97706", command=lambda: self.apply_preset(double_buy=True))
            btn_p1.pack(fill="x", padx=10, pady=3)
            btn_p2 = ctk.CTkButton(grp_preset, text="💥 거래량 폭증 매집주 (1.5배+)", fg_color="#8B5CF6", hover_color="#7C3AED", command=lambda: self.apply_preset(vol_surge=True))
            btn_p2.pack(fill="x", padx=10, pady=3)
            btn_p3 = ctk.CTkButton(grp_preset, text="🛡️ 초저평가 자산주 (PBR≤1.0)", fg_color="#10B981", hover_color="#059669", command=lambda: self.apply_preset(low_pbr=True))
            btn_p3.pack(fill="x", padx=10, pady=3)
            btn_p4 = ctk.CTkButton(grp_preset, text="⚡ RSI 과매도 탈출주", fg_color="#EC4899", hover_color="#DB2777", command=lambda: self.apply_preset(min_score=55))
            btn_p4.pack(fill="x", padx=10, pady=3)

            # 세부 필터 옵션
            grp_filter = ctk.CTkFrame(sidebar)
            grp_filter.pack(fill="x", pady=10, ipadx=5, ipady=5)
            ctk.CTkLabel(grp_filter, text="⚙️ 세부 필터 옵션", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)

            self.var_foreign = ctk.BooleanVar(value=False)
            self.var_organ = ctk.BooleanVar(value=False)
            self.var_double = ctk.BooleanVar(value=False)
            self.var_vol = ctk.BooleanVar(value=False)
            self.var_pbr = ctk.BooleanVar(value=False)

            ctk.CTkCheckBox(grp_filter, text="외국인 최근 3일 순매수", variable=self.var_foreign, command=self.update_filtered_view).pack(anchor="w", padx=10, pady=3)
            ctk.CTkCheckBox(grp_filter, text="기관 최근 3일 순매수", variable=self.var_organ, command=self.update_filtered_view).pack(anchor="w", padx=10, pady=3)
            ctk.CTkCheckBox(grp_filter, text="외인+기관 쌍끌이 순매수", variable=self.var_double, command=self.update_filtered_view).pack(anchor="w", padx=10, pady=3)
            ctk.CTkCheckBox(grp_filter, text="거래량 급증 (20일평균 1.3배+)", variable=self.var_vol, command=self.update_filtered_view).pack(anchor="w", padx=10, pady=3)
            ctk.CTkCheckBox(grp_filter, text="저평가 PBR 1.0 이하만", variable=self.var_pbr, command=self.update_filtered_view).pack(anchor="w", padx=10, pady=3)

            # 실행 버튼들
            self.btn_scan = ctk.CTkButton(
                sidebar, text="🚀 바닥 반등 종목 스캔 시작",
                font=ctk.CTkFont(size=14, weight="bold"),
                height=42, fg_color="#2563EB", hover_color="#1D4ED8",
                command=self.start_scan
            )
            self.btn_scan.pack(fill="x", pady=(15, 5))

            self.btn_export = ctk.CTkButton(
                sidebar, text="📥 검색 결과 CSV 저장",
                fg_color="#059669", hover_color="#047857",
                command=self.export_csv, state="disabled"
            )
            self.btn_export.pack(fill="x", pady=5)

            # [우측 메인 영역]
            right_panel = ctk.CTkFrame(main_container, fg_color="transparent")
            right_panel.pack(side="right", fill="both", expand=True)

            # 진행률 & 상태
            self.progress_bar = ctk.CTkProgressBar(right_panel, height=8)
            self.progress_bar.set(0)
            self.progress_bar.pack(fill="x", pady=(0, 5))
            self.progress_bar.pack_forget()

            self.lbl_status = ctk.CTkLabel(right_panel, text="👈 스캔 시작 버튼을 눌러 반등 종목 분석을 진행하세요.", text_color="#3B82F6", font=ctk.CTkFont(weight="bold"))
            self.lbl_status.pack(anchor="w", pady=(0, 10))

            # 요약 메트릭 카드 4개
            cards_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
            cards_frame.pack(fill="x", pady=(0, 10))

            self.card1_val = self.create_card(cards_frame, "발굴된 종목 수", "0 개", "#3B82F6")
            self.card2_val = self.create_card(cards_frame, "강력 반등 (70점+)", "0 개", "#10B981")
            self.card3_val = self.create_card(cards_frame, "외인+기관 쌍끌이", "0 개", "#F59E0B")
            self.card4_val = self.create_card(cards_frame, "거래량 급증 (1.5배+)", "0 개", "#8B5CF6")

            # 탭뷰 (결과 테이블 / 상세 분석)
            self.tabview = ctk.CTkTabview(right_panel)
            self.tabview.pack(fill="both", expand=True)

            tab_table = self.tabview.add("📋 종목 스캔 결과 리스트")
            tab_detail = self.tabview.add("📊 종목별 심층 차트 & 반등 분석")

            # Tab 1: 결과 테이블 (ttk.Treeview 사용)
            table_frame = ctk.CTkFrame(tab_table)
            table_frame.pack(fill="both", expand=True, padx=5, pady=5)

            columns = (
                "code", "name", "market", "grade", "score", "price",
                "diff_low", "fall_high", "rsi", "vol_ratio", "foreign", "organ"
            )
            self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
            
            headers = {
                "code": ("종목코드", 80),
                "name": ("종목명", 130),
                "market": ("시장", 70),
                "grade": ("등급", 130),
                "score": ("반등점수", 70),
                "price": ("현재가", 90),
                "diff_low": ("52주최저이격률", 100),
                "fall_high": ("52주최고낙폭", 100),
                "rsi": ("RSI(14)", 70),
                "vol_ratio": ("거래량비율", 80),
                "foreign": ("외인3일순매수", 110),
                "organ": ("기관3일순매수", 110),
            }

            for col, (text, width) in headers.items():
                self.tree.heading(col, text=text, command=lambda c=col: self.sort_tree(c, False))
                self.tree.column(col, width=width, anchor="center" if col in ["code", "market", "grade", "score"] else "e")

            # 스크롤바
            scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscrollcommand=scrollbar.set)
            
            self.tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

            # Tab 2: 상세 분석 및 텍스트/차트
            detail_container = ctk.CTkFrame(tab_detail)
            detail_container.pack(fill="both", expand=True, padx=5, pady=5)

            # 좌측 상세 레포트
            self.txt_detail = ctk.CTkTextbox(detail_container, width=450, font=ctk.CTkFont(family="Malgun Gothic", size=13))
            self.txt_detail.pack(side="left", fill="both", padx=(0, 10), pady=5)

            # 우측 차트 박스
            chart_box = ctk.CTkFrame(detail_container)
            chart_box.pack(side="right", fill="both", expand=True, pady=5)

            self.lbl_chart_title = ctk.CTkLabel(chart_box, text="📈 종목을 선택하시면 인터랙티브 Plotly 차트가 생성됩니다.", font=ctk.CTkFont(size=14, weight="bold"))
            self.lbl_chart_title.pack(pady=20)

            self.btn_open_chart = ctk.CTkButton(
                chart_box, text="🌐 웹 브라우저에서 차트 크게 열기 ↗",
                fg_color="#2563EB", hover_color="#1D4ED8",
                command=self.open_chart_in_browser, state="disabled"
            )
            self.btn_open_chart.pack(pady=10)

    def create_card(self, parent, title, val_text, color_hex):
        card = ctk.CTkFrame(parent, fg_color=("white", "#1E293B"), corner_radius=8)
        card.pack(side="left", fill="both", expand=True, padx=5)
        
        lbl_t = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11), text_color="#64748B")
        lbl_t.pack(anchor="w", padx=10, pady=(8, 2))
        
        lbl_v = ctk.CTkLabel(card, text=val_text, font=ctk.CTkFont(size=18, weight="bold"), text_color=color_hex)
        lbl_v.pack(anchor="w", padx=10, pady=(0, 8))
        return lbl_v

    def on_score_slider_change(self, val):
        self.score_label.configure(text=f"{int(val)}점 이상")
        self.update_filtered_view()

    def apply_preset(self, double_buy=False, vol_surge=False, low_pbr=False, min_score=None):
        self.var_double.set(double_buy)
        self.var_vol.set(vol_surge)
        self.var_pbr.set(low_pbr)
        if min_score is not None:
            self.slider_min_score.set(min_score)
            self.score_label.configure(text=f"{min_score}점 이상")
        self.update_filtered_view()

    # -------------------------------------------------------------------------
    # 스캔 비동기 수행 (threading)
    # -------------------------------------------------------------------------
    def start_scan(self):
        market_map = {"전체 (KOSPI + KOSDAQ)": "ALL", "코스피 (KOSPI)": "KOSPI", "코스닥 (KOSDAQ)": "KOSDAQ"}
        market = market_map[self.combo_market.get()]
        top_n = int(self.slider_top_n.get())

        self.btn_scan.configure(state="disabled", text="⏳ 스캔 진행 중...")
        self.progress_bar.pack(fill="x", pady=(0, 5))
        self.progress_bar.set(0)
        self.lbl_status.configure(text=f"시장 종목 정보 수집 중... (0/{top_n})")

        def worker():
            try:
                def cb(curr, total):
                    pct = curr / total
                    self.root.after(0, lambda: self.update_progress(pct, curr, total))

                df_res = run_stock_scan(market=market, top_n=top_n, progress_callback=cb)
                self.root.after(0, lambda: self.on_scan_finished(df_res))
            except Exception as e:
                self.root.after(0, lambda: self.on_scan_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def update_progress(self, pct, curr, total):
        self.progress_bar.set(pct)
        self.lbl_status.configure(text=f"종목 수집 및 반등 확률 분석 중... ({curr}/{total} 완료)")

    def on_scan_finished(self, df_res):
        self.btn_scan.configure(state="normal", text="🚀 바닥 반등 종목 스캔 시작")
        self.progress_bar.pack_forget()
        
        self.scan_data = df_res
        if df_res is not None and not df_res.empty:
            self.btn_export.configure(state="normal")
            self.lbl_status.configure(text=f"✅ 총 {len(df_res)}개 바닥 관심/반등 후보 종목이 발굴되었습니다.")
            self.update_filtered_view()
        else:
            self.lbl_status.configure(text="⚠️ 스캔된 반등 유망 종목이 없습니다.")
            self.clear_table()

    def on_scan_error(self, err):
        self.btn_scan.configure(state="normal", text="🚀 바닥 반등 종목 스캔 시작")
        self.progress_bar.pack_forget()
        messagebox.showerror("스캔 오류", f"스캔 과정에서 오류가 발생하였습니다:\n{err}")

    # -------------------------------------------------------------------------
    # 필터링 & 테이블 갱신
    # -------------------------------------------------------------------------
    def clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def update_filtered_view(self):
        if self.scan_data is None or self.scan_data.empty:
            return

        df = self.scan_data.copy()
        min_score = int(self.slider_min_score.get())
        df = df[df['total_score'] >= min_score]

        if self.var_foreign.get():
            df = df[df['foreign_buy_3d'] > 0]
        if self.var_organ.get():
            df = df[df['organ_buy_3d'] > 0]
        if self.var_double.get():
            df = df[(df['foreign_buy_3d'] > 0) & (df['organ_buy_3d'] > 0)]
        if self.var_vol.get():
            df = df[df['vol_surge_ratio'] >= 1.3]
        if self.var_pbr.get():
            df = df[df['pbr'].notnull() & (df['pbr'] <= 1.0)]

        self.filtered_df = df.reset_index(drop=True)

        # 요약 카드 업데이트
        self.card1_val.configure(text=f"{len(df)} 개")
        high_cnt = len(df[df['total_score'] >= 70])
        self.card2_val.configure(text=f"{high_cnt} 개")
        double_cnt = len(df[(df['foreign_buy_3d'] > 0) & (df['organ_buy_3d'] > 0)])
        self.card3_val.configure(text=f"{double_cnt} 개")
        vol_cnt = len(df[df['vol_surge_ratio'] >= 1.5])
        self.card4_val.configure(text=f"{vol_cnt} 개")

        # 테이블 갱신
        self.clear_table()
        for _, row in self.filtered_df.iterrows():
            vals = (
                str(row['code']),
                str(row['name']),
                str(row['market']),
                str(row['grade']),
                int(row['total_score']),
                f"{row['current_price']:,}원",
                f"+{row['diff_from_52w_low_pct']:.1f}%",
                f"{row['fall_from_52w_high_pct']:.1f}%",
                f"{row['rsi']:.1f}",
                f"{row['vol_surge_ratio']:.2f}배",
                f"{row['foreign_buy_3d']:+,}주",
                f"{row['organ_buy_3d']:+,}주"
            )
            self.tree.insert("", "end", values=vals)

    def sort_tree(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            l.sort(key=lambda t: float(t[0].replace(',', '').replace('원', '').replace('%', '').replace('배', '').replace('주', '')), reverse=reverse)
        except Exception:
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        self.tree.heading(col, command=lambda: self.sort_tree(col, not reverse))

    # -------------------------------------------------------------------------
    # 트리뷰 행 선택 -> 상세 정보 & 차트 생성
    # -------------------------------------------------------------------------
    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items or self.filtered_df is None or self.filtered_df.empty:
            return

        item_vals = self.tree.item(selected_items[0], "values")
        if not item_vals:
            return

        code = item_vals[0]
        matched = self.filtered_df[self.filtered_df['code'] == code]
        if matched.empty:
            return

        row = matched.iloc[0]
        self.selected_code = code
        self.render_detail_info(row)
        self.generate_plotly_chart(row)

    def render_detail_info(self, row):
        reasons_text = "\n".join([f"  • {r}" for r in row['reasons']])
        pbr_str = f"{row['pbr']:.2f}배" if pd.notnull(row['pbr']) else "-"
        per_str = f"{row['per']:.1f}배" if pd.notnull(row['per']) else "-"

        info = f"""📌 {row['name']} ({row['code']})
--------------------------------------------------
■ 시장: {row['market']}
■ 현재가: {row['current_price']:,}원
■ 반등 점수: {row['total_score']} / 100점 ({row['grade']})

💡 핵심 반등 포인트 & 포착 사유:
{reasons_text}

📊 수급 및 가치 평가:
  • PBR: {pbr_str} | PER: {per_str}
  • 최근 3일 외인 순매수: {row['foreign_buy_3d']:+,} 주 (연속 {row['foreign_consec']}일)
  • 최근 3일 기관 순매수: {row['organ_buy_3d']:+,} 주 (연속 {row['organ_consec']}일)
"""
        self.txt_detail.delete("1.0", "end")
        self.txt_detail.insert("1.0", info)

    def generate_plotly_chart(self, row):
        code = row['code']
        name = row['name']
        
        df_chart = fetch_stock_ohlcv(code, days=120)
        if df_chart is not None and len(df_chart) > 0:
            df_chart['MA5'] = df_chart['Close'].rolling(5).mean()
            df_chart['MA20'] = df_chart['Close'].rolling(20).mean()
            df_chart['MA60'] = df_chart['Close'].rolling(60).mean()
            df_chart['RSI'] = calculate_rsi(df_chart['Close'], 14)
            upper, mid, lower, _ = calculate_bollinger_bands(df_chart['Close'], 20, 2.0)
            df_chart['BB_Upper'] = upper
            df_chart['BB_Lower'] = lower

            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                subplot_titles=(f"{name} 일봉 차트 (볼린저밴드/이평선)", "거래량", "RSI (14)"),
                row_heights=[0.6, 0.2, 0.2]
            )

            fig.add_trace(go.Candlestick(
                x=df_chart.index, open=df_chart['Open'], high=df_chart['High'],
                low=df_chart['Low'], close=df_chart['Close'], name="주가",
                increasing_line_color='#EF4444', decreasing_line_color='#3B82F6'
            ), row=1, col=1)

            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA5'], name="5일선", line=dict(color='orange', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA20'], name="20일선", line=dict(color='green', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['MA60'], name="60일선", line=dict(color='purple', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_Upper'], name="BB 상단", line=dict(color='rgba(150,150,150,0.5)', dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_Lower'], name="BB 하단", line=dict(color='rgba(239,68,68,0.7)', dash='dash')), row=1, col=1)

            colors = ['#EF4444' if c >= o else '#3B82F6' for c, o in zip(df_chart['Close'], df_chart['Open'])]
            fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'], name="거래량", marker_color=colors), row=2, col=1)

            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['RSI'], name="RSI(14)", line=dict(color='#8B5CF6')), row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="green", row=3, col=1)

            fig.update_layout(
                height=650, margin=dict(l=20, r=20, t=30, b=20),
                showlegend=False, xaxis_rangeslider_visible=False
            )

            temp_dir = tempfile.gettempdir()
            self.latest_chart_path = os.path.join(temp_dir, f"stock_chart_{code}.html")
            fig.write_html(self.latest_chart_path)

            self.lbl_chart_title.configure(text=f"📈 {name} ({code}) 차트 생성 완료!")
            self.btn_open_chart.configure(state="normal")

    def open_chart_in_browser(self):
        if hasattr(self, 'latest_chart_path') and os.path.exists(self.latest_chart_path):
            webbrowser.open(f"file:///{self.latest_chart_path}")

    def export_csv(self):
        if self.filtered_df is None or self.filtered_df.empty:
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=f"바닥_반등_유망주_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )
        if path:
            self.filtered_df.to_csv(path, index=False, encoding='utf-8-sig')
            messagebox.showinfo("저장 완료", f"파일이 성공적으로 저장되었습니다:\n{path}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = StockFinderDesktopApp()
    app.run()
