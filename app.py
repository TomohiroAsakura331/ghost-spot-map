
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import hmac

st.set_page_config(
    page_title="心霊スポット分析",
    layout="wide"
)

def check_password():
    if st.session_state.get("authenticated", False):
        return True

    st.title("心霊スポット分析")
    st.write("閲覧するにはパスワードを入力してください。")

    password = st.text_input(
        "パスワード",
        type="password"
    )

    if st.button("ログイン"):
        if hmac.compare_digest(
            password,
            st.secrets["APP_PASSWORD"]
        ):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います。")

    return False


if not check_password():
    st.stop()

st.title("心霊スポット総合分析マップ")
st.caption("17要因に基づく分析結果")

html_path = Path(__file__).parent / "composite_report.html"

if html_path.exists():
    html_content = html_path.read_text(encoding="utf-8")

    components.html(
        html_content,
        height=850,
        scrolling=True
    )
else:
    st.error("HTMLファイルが見つかりません。")
