import streamlit as st
import streamlit.components.v1 as components
import os

try:
    st.set_page_config(
        page_title="📋 축의금 / 부조금 내역 조회",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
except Exception:
    pass

current_dir = os.path.dirname(os.path.abspath(__file__))
html_path = os.path.join(os.path.dirname(current_dir), "buju_viewer.html")

if not os.path.exists(html_path):
    html_path = os.path.join(current_dir, "buju_viewer.html")

if os.path.exists(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html_code = f.read()
    components.html(html_code, height=1350, scrolling=True)
else:
    st.error("❌ buju_viewer.html 파일을 찾을 수 없습니다.")
