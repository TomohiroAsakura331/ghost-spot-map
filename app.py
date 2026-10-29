import hmac
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from map3d.render import DATA as MAP3D_DATA
from map3d.render import build_map3d_html
from step5map.render import DATA as STEP5_DATA
from step5map.render import build_step5_html

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


@st.cache_data(show_spinner="順位・未登録候補の地図を準備しています…")
def load_step5_html(data_path_str: str, mtime: float) -> str:
    return build_step5_html(Path(data_path_str))


@st.cache_data(show_spinner=False)
def load_csv(path_str: str, mtime: float) -> pd.DataFrame:
    return pd.read_csv(path_str, dtype={"mesh_code": str, "peak_mesh": str, "spot_id": str})


st.title("心霊スポット総合分析")
st.caption("17要因に基づく分析結果")

tab_2d, tab_3d, tab_step5 = st.tabs(["2D分析マップ", "3D分析マップ", "既存スポット順位・未登録候補"])

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

with tab_step5:
    st.info(
        "既存の心霊スポットを2つの評価で順位づけし、同じ評価で「まだ掲載のない高スコア地域」を示します。"
        "A＝空間交差検証で検証した掲載傾向モデル、B＝H1（仮説の向き・等重みの探索的立地条件）で、AとBは混ぜていません。"
        "どちらも心霊体験の発生確率ではなく、未登録は「心霊スポットがない」ことを意味しません。"
    )
    if STEP5_DATA.exists():
        components.html(
            load_step5_html(str(STEP5_DATA), STEP5_DATA.stat().st_mtime),
            height=880,
            scrolling=False
        )
        st.caption(
            "柱の高さはスコアの3乗×倍率（上位を強調）で、見やすさのための表示です。標高や確率ではありません。"
            "地図右上の一覧から地点・地域を選ぶと、主な要因と注意点を表示します。"
        )
    else:
        st.error("STEP 5 の地図データ（data/step5_map_data.json.gz）が見つかりません。")

    spots_path = BASE_DIR / "data" / "step5_existing_spots_ranking.csv"
    cands_path = BASE_DIR / "data" / "step5_unregistered_candidates.csv"
    if spots_path.exists() and cands_path.exists():
        spots = load_csv(str(spots_path), spots_path.stat().st_mtime)
        cands = load_csv(str(cands_path), cands_path.stat().st_mtime)

        st.subheader("表で見る")
        c1, c2, c3 = st.columns(3)
        pref = c1.selectbox("都県", ["（すべて）"] + sorted(spots.primary_pref.dropna().unique()), key="s5_pref")
        munis = spots if pref == "（すべて）" else spots[spots.primary_pref == pref]
        muni = c2.selectbox("市区町村", ["（すべて）"] + sorted(munis.municipality.dropna().unique()), key="s5_muni")
        order = c3.radio("並び順", ["A 掲載傾向", "B 立地条件（H1）"], horizontal=True, key="s5_order")

        t_spots, t_cands = st.tabs(["既存スポットの順位", "未登録の高スコア地域"])
        with t_spots:
            kinds = st.multiselect(
                "種類", ["具体的地点", "広域代表点（山・公園など）", "位置要確認", "位置不明（評価不可）"],
                default=["具体的地点"], key="s5_kinds"
            )
            t = spots[spots.spot_type.isin(kinds)]
            if pref != "（すべて）":
                t = t[t.primary_pref == pref]
            if muni != "（すべて）":
                t = t[t.municipality == muni]
            t = t.sort_values("rank_B" if order.startswith("B") else "rank_A", na_position="last")
            st.caption(
                f"{len(t):,}件。順位は全スポット中の順位で、同じ1kmメッシュは同点。"
                "A順位(最良〜最悪)＝交差検証の分け方3通りでの幅、B(最小〜最大)＝重み45通りでの幅。"
            )
            st.dataframe(
                t.rename(columns={
                    "rank_A": "A順位", "rank_A_best_of_3splits": "A順位(最良)", "rank_A_worst_of_3splits": "A順位(最悪)",
                    "rank_B": "B順位", "name": "名称", "genre": "カテゴリ", "spot_type": "種類", "address": "所在地",
                    "primary_pref": "都県", "municipality": "市区町村", "score_A_listing_tendency": "A",
                    "score_A_baseline_model": "A(基準モデル)", "A_neighbourhood_mean": "A(周辺9区画平均)",
                    "score_B_H1_location": "B", "score_B_low_under_45_weight_sets": "B(最小)",
                    "score_B_high_under_45_weight_sets": "B(最大)", "main_factors_A": "Aの主な要因",
                    "lowering_factors_A": "Aを下げた要因", "main_factors_B": "Bの主な要因",
                    "auxiliary_records": "補助記録", "caveats": "評価上の注意", "source_url": "掲載元",
                }),
                use_container_width=True, hide_index=True, height=460,
                column_config={"掲載元": st.column_config.LinkColumn("掲載元")},
            )
            st.download_button("この表をCSVで保存", t.to_csv(index=False).encode("utf-8-sig"),
                               file_name="existing_spots_ranking_filtered.csv", mime="text/csv", key="s5_dl1")
        with t_cands:
            cset = st.radio(
                "抽出方法", ["全域A上位1%", "都県内A上位1%", "B（H1）上位1%"], horizontal=True, key="s5_cset",
                help="全域＝首都圏全体での順位、都県内＝同じ予測値を都県ごとに並べ直した順位、B＝参考（仮説スコア）"
            )
            k = cands[cands.candidate_set == cset]
            if pref != "（すべて）":
                k = k[k.prefecture.str.contains(pref, regex=False)]
            if muni != "（すべて）":
                k = k[k.municipalities.str.contains(muni, regex=False)]
            st.caption(f"{len(k):,}地域（隣接する高スコア区画を1地域に統合）。未登録＝心霊スポットがない、ではありません。")
            st.dataframe(
                k.rename(columns={
                    "rank": "順位", "area_id": "地域ID", "n_meshes": "区画数", "prefecture": "都県", "municipalities": "市区町村",
                    "peak_mesh": "頂点メッシュ", "peak_lat": "緯度", "peak_lon": "経度", "peak_score": "頂点スコア",
                    "peak_score_A_overall": "A(全域)", "peak_score_A_within_pref": "A(都県内)", "peak_score_B_H1": "B",
                    "split_pct_min": "A分け方最小", "split_pct_max": "A分け方最大", "main_factors_A": "Aの主な要因",
                    "main_factors_B": "Bの主な要因", "nearest_listed": "最寄りの既存スポット", "nearest_listed_km": "距離km",
                    "similar_existing_spot_meshes": "立地が似た既存スポット", "why_unregistered": "未登録と判断した根拠",
                    "uncertainty": "不確実性",
                }),
                use_container_width=True, hide_index=True, height=460,
            )
            st.download_button("この表をCSVで保存", k.to_csv(index=False).encode("utf-8-sig"),
                               file_name="unregistered_candidates_filtered.csv", mime="text/csv", key="s5_dl2")
    else:
        st.error("STEP 5 の表データ（data/step5_*.csv）が見つかりません。")
