# -*- coding: utf-8 -*-
"""STEP 5.7：E56 環境スコア可視化（2D・3D地図、安定度、要因別寄与、スポット検索、未登録候補）。

既存のトップページ（app.py）は変更せず、ページとして追加している。
パスワードはトップページと同じ方式（st.secrets["APP_PASSWORD"]、セッション共通の authenticated）。
"""
import hmac

import streamlit as st

st.set_page_config(page_title="E56 環境スコア可視化（STEP 5.7）", layout="wide")


def check_password() -> bool:
    if st.session_state.get("authenticated", False):
        return True
    st.title("心霊スポット分析")
    st.write("閲覧するにはパスワードを入力してください。")
    password = st.text_input("パスワード", type="password", key="s57_password")
    if st.button("ログイン", key="s57_login"):
        if hmac.compare_digest(password, st.secrets["APP_PASSWORD"]):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    return False


if not check_password():
    st.stop()

from s57viz.page import main  # noqa: E402  （認証後に読み込む）

main()
