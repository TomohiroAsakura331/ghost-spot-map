import hmac
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from map3d.render import DATA as MAP3D_DATA
from map3d.render import build_map3d_html

st.set_page_config(
    page_title="心霊スポット分析",
    layout="wide"
)

BASE_DIR = Path(__file__).parent


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


@st.cache_data(show_spinner=False)
def load_2d_html(path_str: str, mtime: float) -> str:
    return Path(path_str).read_text(encoding="utf-8")


@st.cache_data(show_spinner="3D地図を準備しています…")
def load_3d_html(data_path_str: str, mtime: float) -> str:
    return build_map3d_html(Path(data_path_str))


st.title("心霊スポット総合分析")
st.caption("17要因に基づく分析結果")

tab_2d, tab_3d = st.tabs(["2D分析マップ", "3D分析マップ"])

with tab_2d:
    html_path = BASE_DIR / "composite_report.html"
    if html_path.exists():
        components.html(
            load_2d_html(str(html_path), html_path.stat().st_mtime),
            height=850,
            scrolling=True
        )
    else:
        st.error("HTMLファイルが見つかりません。")

with tab_3d:
    st.info(
        "本マップは17の立地・環境要因に基づく総合スコアを立体的に可視化したものです。"
        "高さは心霊体験の実際の発生確率を示すものではありません。"
    )
    if MAP3D_DATA.exists():
        components.html(
            load_3d_html(str(MAP3D_DATA), MAP3D_DATA.stat().st_mtime),
            height=860,
            scrolling=False
        )
        st.caption(
            "対象範囲は既存分析と同じ首都圏（1都7県・東京都島しょ）の1kmメッシュです。"
            "スコア・順位は composite_report.html / mesh_composite.csv の既存値をそのまま表示しており、"
            "高さ倍率・強調・平滑化は見た目だけを変えます。"
        )
    else:
        st.error("3D地図データ（data/map3d_data.json.gz）が見つかりません。")
