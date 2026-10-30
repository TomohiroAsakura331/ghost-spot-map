"""Authenticated viewer for the frozen STEP 5.8 research results."""
import hmac
import os

import pandas as pd
import streamlit as st

from s58viz.data import PREFS, ROOT, filter_table, read_table
from s58viz.render import build
from s58viz.research import research_page, sources_page

st.set_page_config(page_title="E58｜心霊スポットの環境分析", page_icon="◈", layout="wide")


def check_password():
    if st.session_state.get("authenticated", False):
        return True
    st.title("E58｜心霊スポットの環境分析")
    st.caption("STEP 5.8 · 都県別ランキング上位30% · 2026-10-30")
    try:
        expected = st.secrets.get("APP_PASSWORD", "")
    except FileNotFoundError:
        expected = ""
    expected = expected or os.environ.get("APP_PASSWORD", "")
    if not isinstance(expected, str) or not expected:
        st.error("閲覧パスワードが未設定です。管理者が APP_PASSWORD を設定してから起動してください。")
        st.caption("ローカルでは .streamlit/secrets.toml、Streamlit Community Cloud ではアプリ設定の Secrets に設定します。")
        return False
    with st.form("login"):
        password = st.text_input("パスワード", type="password")
        submitted = st.form_submit_button("ログイン")
    if submitted:
        if hmac.compare_digest(password.encode("utf-8"), expected.encode("utf-8")):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    return False


if not check_password():
    st.stop()


@st.cache_data(show_spinner=False)
def table(name):
    return read_table(name)


@st.cache_data(show_spinner="E58の地図を準備しています…", max_entries=18)
def map_html(kind, prefecture, revision):
    return build(kind, prefecture)


st.sidebar.title("E58 · STEP 5.8")
page = st.sidebar.radio("ページ", ["概要", "研究詳細", "2D E58マップ", "3D E58マップ", "ランキング・検索", "データ出典"], key="page")
pref = st.sidebar.selectbox("都県で絞り込み", ["すべて"] + PREFS, key="prefecture")
st.sidebar.caption("地図・ランキングに適用。E58は全域で算出済みの順位点を保ちます。")
st.sidebar.caption("正式な採用対象 679件\n\n住居33件は名称・地点を非表示")
if st.sidebar.button("ログアウト"):
    st.session_state.clear()
    st.rerun()

st.title("心霊スポットの環境分析｜E58")
st.caption("STEP 5.8 正式版 · 1都7県・1kmメッシュ · ランキング取得日 2026-10-30")
st.info("E58は、都県別ランキング上位30%のスポットの掲載に関連する環境を表す順位点です。心霊体験の発生確率ではありません。同じメッシュのスポットは同じスコアです。")

required = ["e58_map.json.gz", "e58_mesh.csv.gz", "e58_public_spots.csv.gz", "e58_importance.csv", "e58_adoption.csv"]
missing = [name for name in required if not (ROOT / "data" / name).exists()]
if missing:
    st.error("正式版データが不足しています：" + "、".join(missing))
    st.stop()

if page == "概要":
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("採用スポット", "679件")
    c2.metric("E58学習の陽性", "210メッシュ")
    c3.metric("順位点の基準", "31,303メッシュ")
    c4.metric("重要度1位", "森林割合")
    st.subheader("都県ごとに上位30%を採用して再分析")
    st.write("1都7県の掲載2,252件から、都県別ランキングの上位30%を切り上げて679件採用しました。11環境要因を人口密度・道路密度・都県で調整し、要因を外したときの予測の悪化から重要度を評価しました。")
    st.success("森林割合は、11要因で唯一、要因を外したときのLogLoss悪化の95%区間が0を上回りました。調整後の寄与は森林4〜6割で高い山型です。")
    st.write("病院・診療所までの距離が2位、墓地までの距離が3位ですが、森林以外の個別要因は95%区間が0をまたぎます。11要因全体の改善も不確かです。")
    st.subheader("地図と表の読み方")
    st.markdown("- **2D**：E58、安定度、11要因・要因群の寄与、採用スポットを重ねて確認。\n- **3D**：柱と曲面でスコアの分布を確認。高さ・平滑化は表示上の操作です。\n- **ランキング・検索**：サイトの都県内順位と、メッシュのE58順位を区別して表示。\n- **研究詳細**：選定、学習方法、森林の結果、E58の定義と限界を確認。")
    st.caption("図示する32,042メッシュのうち739は保留区画で参考値です。公開リスト646件のうち641件に座標があり、住居33件と座標不明5件はピン表示しません。")
elif page == "研究詳細":
    research_page(table)
elif page in {"2D E58マップ", "3D E58マップ"}:
    kind = "2d" if page.startswith("2D") else "3d"
    st.subheader(f"{kind.upper()} E58マップ｜{pref}")
    if kind == "3d":
        st.warning("高さはE58スコアの表現です。実地形・標高や発生確率を示しません。曲面は表示のための補間・平滑化で、新しい分析結果ではありません。")
    st.caption("色はE58の順位帯（3Dの上位1%は黄色）、安定度は15条件で上位5%に入る回数。2Dの寄与表示は青＝押し下げ、橙＝押し上げ。ピンク＝採用スポット、広域代表点は区別して表示します。")
    try:
        revision = ((ROOT / f"s58viz/template_{kind}.html").stat().st_mtime_ns, (ROOT / "data/e58_map.json.gz").stat().st_mtime_ns)
        st.iframe(map_html(kind, pref, revision), height=920, alt=f"{pref}の{kind.upper()} E58環境スコア地図")
    except (FileNotFoundError, ValueError) as exc:
        st.error(f"地図を表示できません：{exc}")
    st.caption("スコアの基準は全域31,303メッシュで固定。都県の選択は表示だけを絞ります。スポットはランキングの都県、メッシュは地理的な所属で絞るため、県境の橋などでは所属が異なることがあります。")
    st.caption("WebGLとgzip展開に対応したブラウザが必要です。背景地図は初期状態では非表示で、選択時のみ外部タイルを取得します。出典は地図内と「データ出典」に表示しています。")
elif page == "ランキング・検索":
    is_public = st.radio("表示対象", ["採用スポット", "メッシュ"], horizontal=True) == "採用スポット"
    df = table("e58_public_spots.csv.gz" if is_public else "e58_mesh.csv.gz")
    pcol, mcol = ("都県", "市区町村") if is_public else ("primary_pref", "municipality")
    regional = df if pref == "すべて" else df[df[pcol].eq(pref)]
    c1, c2 = st.columns([1, 2])
    muni = c1.selectbox("市区町村", ["すべて"] + sorted(regional[mcol].dropna().unique().tolist()))
    query = c2.text_input("検索", placeholder="スポット名・市区町村・メッシュ番号")
    score_min = st.slider("E58の下限（全域の順位点）", 0, 100, 0)
    reference = st.checkbox("保留区画の参考値も含める", value=is_public)
    filtered = filter_table(df, pref, muni, query, score_min, is_public, reference)
    if is_public:
        order = st.selectbox("並び順", ["E58が高い順", "サイトの都県内順位"])
        filtered = filtered.sort_values(["score_E58", "都県内ランキング順位"], ascending=[False, True], na_position="last") if order.startswith("E58") else filtered.sort_values(["都県", "都県内ランキング順位"])
        columns = ["スポット名", "都県", "市区町村", "カテゴリ", "都県内ランキング順位", "都県内掲載総数", "上位割合（%）", "score_E58", "rank_E58", "1kmメッシュ", "座標の確かさ", "inD", "E58の主な押し上げ要因", "個別ページURL"]
        st.caption(f"該当 {len(filtered):,}件。正式な採用679件のうち住居33件を除いた646件を検索できます。座標不明5件も表には含みます。サイト順位は都県内の掲載ランキング、E58順位は全域の分析対象メッシュ内の順位です。")
    else:
        filtered = filtered.sort_values("score_E58", ascending=False)
        columns = ["mesh_code", "primary_pref", "municipality", "stratum3", "score_E58", "rank_E58", "E58安定度_上位5パーセント", "inD", "n_top30", "hidden_residences", "E58の主な押し上げ要因"]
        st.caption(f"該当 {len(filtered):,}メッシュ。保留区画は学習に使わない参考値で、E58順位を付けていません。")
    labels = {"score_E58": "E58（順位点）", "rank_E58": "全域E58メッシュ順位", "mesh_code": "メッシュ", "primary_pref": "都県", "municipality": "市区町村", "stratum3": "地域区分", "inD": "分析対象（Falseは参考値）", "hidden_residences": "非表示の住居件数", "n_top30": "採用スポット数"}
    shown = filtered[columns].rename(columns=labels)
    st.dataframe(shown, hide_index=True, width="stretch", height=440, column_config={"個別ページURL": st.column_config.LinkColumn("掲載元"), "E58（順位点）": st.column_config.NumberColumn(format="%.2f")})
    st.download_button("表示中の表をCSVで保存", shown.to_csv(index=False).encode("utf-8-sig"), file_name="e58_filtered.csv", mime="text/csv")
    st.caption("安定度は15条件のうち上位5%に入った割合（%）です。サイト順位・E58順位とも表示の絞り込みでは再計算しません。")
    if len(filtered):
        st.subheader("1kmメッシュの要因寄与")
        options = filtered.index[:200].tolist()
        if len(filtered) > 200:
            st.caption("詳細選択は表示順の先頭200件です。市区町村や検索で対象を絞り込めます。")
        def label(index):
            row = filtered.loc[index]
            return f"{row['スポット名']}｜{row['都県']} {row['市区町村']}" if is_public else f"{row['mesh_code']}｜{row['primary_pref']} {row['municipality']}"
        selected = st.selectbox("詳細を見る対象", options, format_func=label)
        row = filtered.loc[selected]
        if pd.isna(row.score_E58):
            st.info("この地点は分析対象メッシュ外、または座標不明のため、E58と寄与を表示できません。")
        else:
            if not bool(row.inD):
                st.warning("保留区画の参考値です。学習には使っていません。")
            if is_public and str(row["座標の確かさ"]).startswith("C"):
                st.warning("広域代表点です。メッシュのスコアは山・湖・公園などの場所全体を表しません。")
            from s58viz.research import FACTORS
            contrib = pd.DataFrame({"要因": [f[0] for f in FACTORS], "寄与（対数オッズ）": [row['cE58_' + f[1]] for f in FACTORS]}).set_index("要因")
            st.bar_chart(contrib, horizontal=True, sort=False, color="#c4307a")
            st.dataframe(contrib, width="stretch")
            st.caption(f"寄与の合計 {contrib.iloc[:, 0].sum():.4f}＝E58の元の値（対数オッズ）{row.E58_logit:.4f}。順位点を足し合わせるものではありません。寄与は因果効果や要因の重要度とは異なり、トンネル・橋の正の寄与も確かな効果を意味しません。")
else:
    sources_page()
