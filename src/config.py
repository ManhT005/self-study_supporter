# src/config.py (tạo mới nếu chưa có, dùng chung cho toàn project)
import os
import streamlit as st

def get_api_key(key_name: str) -> str | None:
    # Ưu tiên st.secrets khi chạy trên Streamlit Cloud
    try:
        return st.secrets[key_name]
    except (KeyError, FileNotFoundError):
        return os.getenv(key_name)