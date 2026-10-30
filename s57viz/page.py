# -*- coding: utf-8 -*-
"""STEP 5.7 E56 環境スコア可視化（ghost-spot-map の追加ページ本体）。

- 新しい学習・予測はしない。STEP 5.6 の E56・安定度（23条件）・要因別寄与などを data/s57_* に転記した値をそのまま表示する。
- 2D地図（deck.gl 8.9.36）・3D地図（three.js r160）は s57viz/ のHTMLを components.html で埋め込む（ライブラリ同梱、CDN不要）。
- 必要なのは streamlit だけ（pandas・numpy・altair は streamlit に含まれる）。
- ページ（pages/）から main() を呼ぶ。パスワード確認はページ側で行う。
"""
from __future__ import annotations

from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from .render import DATA as MAP_DATA
from .render import build_2d_html, build_3d_html

BASE = Path(__file__).resolve().parent.parent   # リポジトリのルート
# 幅の指定：新しい Streamlit（1.50以降）は width="stretch"、古い版は **WIDE
_V = tuple(int(x) for x in st.__version__.split(".")[:2])
WIDE = {"width": "stretch"} if _V >= (1, 50) else {"use_container_width": True}
DATA = BASE / "data"

F11 = ['elev_mean_m', 'slope_mean_deg', 'forest_pct', 'f19_terrain_horizon_deg', 'f08_temp_jan_c', 'f04_popcenter_dist_m',
       'f05_medical_dist_m', 'f12_osm_cemetery_dist_m', 'f14_waterarea_dist_m', 'f15_tunnel_dist_m', 'f16_bridge_dist_m']
FN = ['標高', '傾斜', '森林割合', '地形の閉鎖性（遮蔽角）', '1月の気温', '人口中心からの距離', '病院・診療所までの距離', '墓地までの距離',
      '水辺までの距離', 'トンネルまでの距離', '橋までの距離']
GROUPS = ['地形・気候群', '墓地', '水辺', 'トンネル・橋', '生活施設・人口中心']
NCOND = 23
CAUTION = ("E56 は「心霊スポットの掲載傾向に関連する環境要因」についてモデルが評価した値です。"
           "心霊現象の実在・心霊体験の起こりやすさ・霊の強さを示すものではありません。")


# ---------- データ（キャッシュ：ファイル更新時刻をキーにする）
@st.cache_data(show_spinner="E56 2D地図を準備しています…")
def s57_html_2d(path: str, mtime: float) -> str:
    return build_2d_html(Path(path))


@st.cache_data(show_spinner="E56 3D地図を準備しています…")
def s57_html_3d(path: str, mtime: float) -> str:
    return build_3d_html(Path(path))


@st.cache_data(show_spinner=False)
def s57_load_tables(mtime: float):
    mesh = pd.read_csv(DATA / "s57_mesh.csv.gz", dtype={"mesh_code": str})
    spots = pd.read_csv(DATA / "s57_spots.csv", dtype={"mesh_code": str, "spot_id": str})
    cands = pd.read_csv(DATA / "s57_candidates.csv", dtype={"代表区画": str})
    return mesh, spots, cands


def mtime(p: Path) -> float:
    return p.stat().st_mtime if p.exists() else 0.0


# ---------- 共通の小部品
def contrib_chart(values: dict, title: str):
    df = pd.DataFrame({"要因": list(values), "寄与": list(values.values())})
    df["向き"] = np.where(df["寄与"] >= 0, "押し上げ", "押し下げ")
    order = df.sort_values("寄与", ascending=False)["要因"].tolist()
    ch = (alt.Chart(df, title=title).mark_bar().encode(
        y=alt.Y("要因:N", sort=order, title=None, axis=alt.Axis(labelLimit=220)),
        x=alt.X("寄与:Q", title="寄与（対数オッズ）"),
        color=alt.Color("向き:N", scale=alt.Scale(domain=["押し上げ", "押し下げ"], range=["#d66025", "#2166ac"]), legend=None),
        tooltip=["要因", alt.Tooltip("寄与:Q", format="+.3f")]).properties(height=28 * len(df) + 30))
    rule = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#555").encode(x="x:Q")
    st.altair_chart(ch + rule, **WIDE)


def score_compare_chart(vals: dict, title: str):
    df = pd.DataFrame({"スコア": list(vals), "順位点": list(vals.values())}).dropna()
    ch = (alt.Chart(df, title=title).mark_bar(color="#2a78d6").encode(
        y=alt.Y("スコア:N", sort=list(vals), title=None, axis=alt.Axis(labelLimit=220)), x=alt.X("順位点:Q", scale=alt.Scale(domain=[0, 100]), title="順位点（0〜100）"),
        tooltip=["スコア", alt.Tooltip("順位点:Q", format=".2f")]).properties(height=34 * len(df) + 30))
    st.altair_chart(ch, **WIDE)


def fmt(v, d=2):
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:,.{d}f}"




def main():
    # ---------- ページ
    PAGES = ["1. 研究概要", "2. 2Dスコアマップ", "3. 3Dスコアマップ", "4. スポット・候補の詳細分析"]
    try:  # ?view=1〜4 で開く表示を指定できる（発表用の直接リンク）
        _q = int(st.query_params.get("view", "1")) - 1
    except Exception:
        _q = 0
    page = st.sidebar.radio("E56 の表示", PAGES, index=min(max(_q, 0), len(PAGES) - 1), key="s57_view")
    st.sidebar.caption(CAUTION)
    st.sidebar.caption("データ：STEP 5.6（E56＝モデルD、23条件の安定度）。本アプリでは再計算していません。")

    if page == PAGES[0]:
        st.title("E56 環境スコア可視化システム（STEP 5.7）")
        st.info(CAUTION)
        st.subheader("研究の目的")
        st.markdown("""
    首都圏（1都7県）の1kmメッシュについて、心霊スポットとして**掲載されやすい場所の環境条件**を、GIS とロジスティック回帰で調べています。
    STEP 5.6 では、トンネルや橋そのものがスポットとして掲載されていることによる見かけの関連を取り除くため、
    **トンネル・橋だけが掲載されている区画を学習から外したモデル（モデルD）**で環境要因の評価値 **E56** を作りました。
    このアプリは、その結果を地図・3D・グラフで確認するためのものです（新しい学習や予測はしていません）。
    """)
        st.subheader("使用データ")
        st.markdown("""
    - **区画**：首都圏本土の3次メッシュ（約1km四方）。分析対象 31,303 区画＋保留区画 739（広域代表点のみの区画、参考値）。
    - **心霊スポット**：全国心霊マップの掲載 2,150 件（具体的地点 1,094 件、広域の代表点 1,033 件、位置不明 23 件）。原典に位置精度の記載はなく、現地確認もしていません。
    - **調整に使った変数**：都県・人口密度（2020年国勢調査）・道路密度（OpenStreetMap）。E56 はこれらを同じ値にそろえたときの環境要因の差です。
    """)
        st.subheader("11の環境要因")
        st.dataframe(pd.DataFrame({
            "要因": FN,
            "内容・出典": ["DEMの平均標高（国土地理院）", "DEMから計算した平均傾斜（国土地理院）", "森林の面積割合（国土数値情報 土地利用2021）",
                       "周囲の地形による見通しの悪さ（DEMから計算）", "1月の平年気温（1991–2020平年値）", "人口重心までの距離（2020年国勢調査）",
                       "病院・診療所までの距離（国土数値情報 医療機関2020）", "墓地までの距離（OpenStreetMap）", "河川・湖沼などの水域までの距離（地理院地図ベクトル）",
                       "道路トンネルまでの距離（地理院地図ベクトル）", "橋・高架までの距離（地理院地図ベクトル）"],
            "要因群": ["地形・気候群"] * 5 + ["生活施設・人口中心"] * 2 + ["墓地", "水辺", "トンネル・橋", "トンネル・橋"]}),
            hide_index=True, **WIDE)
        st.caption("距離は1kmメッシュの中心から最寄りの地物までの距離（対数変換して使用）。")
        st.subheader("E56 スコアの意味")
        st.markdown(f"""
    - **E56 の値**：モデルの予測（対数オッズ）から、11要因を訓練データの中央値に置き換えたときの予測を引いたもの＝「11要因によってどれだけ掲載されやすく評価されたか」。
      空間交差検証（20kmブロック×5組、5通りの分け方の平均）で、評価する区画のデータは学習に使っていません。
    - **E56 スコア（0〜100）**：分析対象 31,303 区画の中での順位点。99 以上＝上位1%。地図の色・3Dの高さはこの値です。
    - **要因別寄与**：E56 の値は11要因の寄与の和にちょうど分かれます。要因群の寄与はその合計です。要因どうしに相関があるため、**因果効果ではありません**。
    - **安定度（k/{NCOND}）**：モデル（トンネル・橋の扱い4通り＋感度）、空間交差検証の分け方、緩衝帯、大地域での外挿、都県を外した予測、
      座標の確かさ、要因の組み合わせを変えた **{NCOND}条件** のうち、その区画が上位5%に入った条件の数。19/23 以上（8割以上）を「安定上位」としています。
    - **未登録候補**：使用した心霊スポットデータに掲載が確認されなかった一般区画のうち、E56 が高い区画。**心霊体験が起こると予測された場所ではありません。**
    """)
        st.subheader("分析上の限界")
        st.markdown("""
    - 掲載傾向の分析であり、心霊体験の発生確率・因果関係は推定していません。掲載サイトの偏り（有名な場所・アクセスしやすい場所）を含みます。
    - トンネル・橋の距離の効果は、トンネル・橋そのものが掲載されていることによる重なりが大きかったため、E56 ではトンネル・橋だけの掲載区画を学習から外しています。
    - 環境要因全体の寄与は小さく、E56 の上位1%は分析条件によって約半分が入れ替わります。安定度と合わせて見てください。
    - 都市部（人口4,000人/km²以上）の中では、11要因で掲載区画を見分けることはほとんどできませんでした。
    - 同じ1kmメッシュのスポットは同じスコア・同じ順位になります（区画単位の評価）。
    """)
        with st.expander("参考：STEP 5.6 の要因の重要度と安定性"):
            st.image(str(BASE / "s57viz" / "assets" / "s56_fig01_importance_by_model.png"), **WIDE)
            st.image(str(BASE / "s57viz" / "assets" / "s56_fig03_stability.png"), **WIDE)

    elif page == PAGES[1]:
        st.title("2Dスコアマップ")
        st.caption("E56スコア・安定度・要因別寄与を切り替え、既存スポットと未登録候補を重ねて表示します。地図上の操作はブラウザ内で処理するため、絞り込みを変えても再読み込みは起きません。" + CAUTION)
        if MAP_DATA.exists():
            components.html(s57_html_2d(str(MAP_DATA), mtime(MAP_DATA)), height=880, scrolling=False)
        else:
            st.error("地図データ（data/s57_map_data.json.gz）が見つかりません。")

    elif page == PAGES[2]:
        st.title("3Dスコアマップ")
        st.warning("高さは **E56 の環境評価値**（表示用に変換）です。実際の標高・心霊現象の強さ・霊の存在範囲ではありません。高さの倍率や平滑化は見た目だけを変え、スコアの数値は変わりません。")
        if MAP_DATA.exists():
            components.html(s57_html_3d(str(MAP_DATA), mtime(MAP_DATA)), height=880, scrolling=False)
            st.caption("3Dメッシュ（柱）方式＝各1kmメッシュの値そのもの（基本）。3D曲面方式＝隣り合う区画の値だけを平均した表示上の平滑化で、"
                       "各頂点の高さは周囲（平滑化回数＋1区画以内）の元の区画の最大値を超えないよう上限を設けています。2km柱は2×2区画の平均（表示用の集約）。")
        else:
            st.error("地図データ（data/s57_map_data.json.gz）が見つかりません。")

    else:
        st.title("スポット・候補の詳細分析")
        mesh, spots, cands = s57_load_tables(mtime(DATA / "s57_mesh.csv.gz"))
        mi = mesh.set_index("mesh_code")
        tab1, tab2, tab3, tab4 = st.tabs(["既存スポットの検索", "未登録候補の検索", "要因別寄与の比較", "モデル間のスコア比較"])

        with tab1:
            c1, c2, c3 = st.columns([2, 1, 1])
            q = c1.text_input("スポット名・市区町村で検索", "")
            pref = c2.selectbox("都県", ["すべて"] + sorted(spots["都県"].dropna().unique().tolist()))
            tier = c3.selectbox("座標の確かさ", ["すべて"] + sorted(spots["座標の確かさ"].dropna().unique().tolist()))
            sv = spots.copy()
            if q:
                sv = sv[sv["スポット名"].str.contains(q, case=False, na=False) | sv["市区町村"].fillna("").str.contains(q, na=False)]
            if pref != "すべて":
                sv = sv[sv["都県"] == pref]
            if tier != "すべて":
                sv = sv[sv["座標の確かさ"] == tier]
            sv = sv.sort_values("STEP5.6順位（E56）", na_position="last")
            st.caption(f"{len(sv):,} 件（E56順）")
            show = sv[["STEP5.6順位（E56）", "スポット名", "都県", "市区町村", "カテゴリ", "座標の確かさ", "E56スコア", "k5", "E55スコア（STEP5.5）", "STEP5のA順位", "STEP5のB順位"]].rename(
                columns={"STEP5.6順位（E56）": "E56順位", "k5": f"安定度（/{NCOND}）", "E55スコア（STEP5.5）": "E55スコア"})
            st.dataframe(show.head(300), hide_index=True, **WIDE, height=280)
            if len(sv):
                opts = (sv["スポット名"] + "（" + sv["市区町村"].fillna("") + "）").tolist()
                pick = st.selectbox("詳細を見るスポット", range(len(opts)), format_func=lambda k: opts[k])
                r = sv.iloc[pick]
                a, b, c, d = st.columns(4)
                a.metric("E56スコア", fmt(r["E56スコア"]))
                b.metric("E56順位", "—" if pd.isna(r["STEP5.6順位（E56）"]) else f"{int(r['STEP5.6順位（E56）'])}位")
                c.metric("安定度", "—" if pd.isna(r["k5"]) else f"{int(r['k5'])}/{NCOND}")
                d.metric("E55（STEP 5.5）", fmt(r["E55スコア（STEP5.5）"]))
                st.markdown(f"**{r['スポット名']}**　{r['都県']} {r['市区町村'] or ''}｜{r['カテゴリ']}｜{r['座標の確かさ']}")
                st.markdown(f"- 上位3つの押し上げ要因（E56）：{r['E56の主な押し上げ要因'] or '—'}\n- STEP 5.6 の判定：{r['STEP5.6の判定'] or '—'}\n- E55 の高評価の由来：{r['E55高評価の由来'] or '—'}")
                if r["same_mesh_n"] > 1:
                    st.warning(f"同じ1kmメッシュに {int(r['same_mesh_n'])} 件の掲載があり、すべて同じ環境スコア・同じ順位になります（区画単位の評価）。")
                if str(r["座標の確かさ"]).startswith("C"):
                    st.warning("広域の代表点（山・公園など）です。区画のスコアは場所全体の条件ではありません。")
                if isinstance(r["mesh_code"], str) and r["mesh_code"] in mi.index:
                    m = mi.loc[r["mesh_code"]]
                    l, rr = st.columns(2)
                    with l:
                        contrib_chart({FN[j]: m[f"cE56_{c}"] for j, c in enumerate(F11)}, "11要因の寄与（E56）")
                    with rr:
                        contrib_chart({g: m[f"G_{g}"] for g in GROUPS}, "要因群の寄与（E56）")
                        score_compare_chart({"E56（STEP 5.6）": m["score_E56"], "E55（STEP 5.5）": m["score_E55"], "A（STEP 5）": m["score_A_step5"],
                                             "B（STEP 5・H1）": m["score_B_H1_step5"]}, "モデル間のスコア比較（この区画）")
                    st.caption("寄与は要因どうしの相関の影響を受けるため、因果効果ではありません。")
                if isinstance(r["source_url"], str):
                    st.markdown(f"[掲載元ページ]({r['source_url']})")

        with tab2:
            st.info("未登録候補＝使用した心霊スポットデータに掲載が確認されなかった区画。実際にスポットがない、または心霊体験が起こると予測された、という意味ではありません。")
            c1, c2, c3, c4 = st.columns(4)
            cset = c1.selectbox("候補の種類", ["安定上位（19/23条件以上で上位5%）", "E56上位1%"])
            cp = c2.selectbox("都県 ", ["すべて"] + sorted(mesh.primary_pref.dropna().unique().tolist()))
            cs_ = c3.selectbox("地域区分", ["すべて", "都市", "郊外・農村", "山間"])
            kmin = c4.slider("安定度の下限", 0, NCOND, 19 if cset.startswith("安定") else 0)
            mv = mesh[(mesh.cand_stable if cset.startswith("安定") else mesh.cand_top1)].copy()
            if cp != "すべて":
                mv = mv[mv.primary_pref == cp]
            if cs_ != "すべて":
                mv = mv[mv.stratum3 == cs_]
            mv = mv[mv.k5 >= kmin].sort_values(["score_E56", "k5"], ascending=False)
            st.caption(f"{len(mv):,} 区画")
            st.dataframe(mv[["mesh_code", "primary_pref", "municipality", "stratum3", "score_E56", "k5", "score_E55", "top3_E56"]].rename(columns={
                "mesh_code": "メッシュコード", "primary_pref": "都県", "municipality": "市区町村", "stratum3": "地域区分", "score_E56": "E56スコア", "k5": f"安定度（/{NCOND}）",
                "score_E55": "E55スコア", "top3_E56": "主な押し上げ要因"}), hide_index=True, **WIDE, height=300)
            if len(mv):
                pk = st.selectbox("詳細を見る区画", mv.mesh_code.tolist(), format_func=lambda c: f"{c}（{mi.loc[c, 'municipality']}、E56 {mi.loc[c, 'score_E56']:.2f}、安定度 {int(mi.loc[c, 'k5'])}/{NCOND}）")
                m = mi.loc[pk]
                area = m.area_stable if cset.startswith("安定") else m.area_top1
                sel = cands[cands["候補セット"].str.startswith("23" if cset.startswith("安定") else "E56")]
                ar = sel[sel["順位"] == area]
                if len(ar):
                    a0 = ar.iloc[0]
                    st.markdown(f"**地域 {int(area)}**：{a0['都県']} {a0['市区町村']}｜{int(a0['区画数'])}区画｜地域区分 {a0['地域区分']}｜主な押し上げ要因群（地域平均）：{a0['主な押し上げ要因群']}")
                l, rr = st.columns(2)
                with l:
                    contrib_chart({FN[j]: m[f"cE56_{c}"] for j, c in enumerate(F11)}, f"11要因の寄与（メッシュ {pk}）")
                with rr:
                    contrib_chart({g: m[f"G_{g}"] for g in GROUPS}, "要因群の寄与")
                    score_compare_chart({"E56（STEP 5.6）": m["score_E56"], "E55（STEP 5.5）": m["score_E55"], "A（STEP 5）": m["score_A_step5"],
                                         "B（STEP 5・H1）": m["score_B_H1_step5"]}, "モデル間のスコア比較")

        with tab3:
            st.markdown("区画を地域区分・E56の高さで分け、要因群の寄与の平均を比べます（E56の値＝寄与の合計）。")
            g = st.radio("集計単位", ["地域区分（都市・郊外・山間）", "都県"], horizontal=True)
            top = st.radio("対象区画", ["分析対象すべて", "E56上位5%", "E56上位1%", "安定上位の未登録候補"], horizontal=True)
            d = mesh[mesh.inD.astype(bool)]
            d = {"分析対象すべて": d, "E56上位5%": d[d.score_E56 >= 95], "E56上位1%": d[d.score_E56 >= 99], "安定上位の未登録候補": d[d.cand_stable.astype(bool)]}[top]
            key = "stratum3" if g.startswith("地域") else "primary_pref"
            agg = d.groupby(key)[[f"G_{x}" for x in GROUPS]].mean().reset_index().melt(id_vars=key, var_name="要因群", value_name="平均寄与")
            agg["要因群"] = agg["要因群"].str[2:]
            st.altair_chart(alt.Chart(agg).mark_bar().encode(
                x=alt.X(f"{key}:N", title=None), xOffset="要因群:N", y=alt.Y("平均寄与:Q", title="平均寄与（対数オッズ）"),
                color=alt.Color("要因群:N", scale=alt.Scale(domain=GROUPS, range=["#1baf7a", "#7d4fc4", "#2a78d6", "#eb6834", "#9e9d98"])),
                tooltip=[key, "要因群", alt.Tooltip("平均寄与:Q", format="+.3f")]).properties(height=360), **WIDE)
            st.caption(f"対象 {len(d):,} 区画。寄与は因果効果ではありません。")

        with tab4:
            d = mesh[mesh.inD.astype(bool)]
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**上位区画の重なり（E55 と E56）**")
                rows = []
                for q_ in (1, 5, 10):
                    a_ = set(d.mesh_code[d.score_E55 >= 100 - q_]); b_ = set(d.mesh_code[d.score_E56 >= 100 - q_])
                    rows.append({"上位": f"{q_}%", "E55の区画数": len(a_), "E56の区画数": len(b_), "共通": len(a_ & b_), "共通の割合（E55基準）": f"{len(a_ & b_) / len(a_) * 100:.0f}%"})
                st.dataframe(pd.DataFrame(rows), hide_index=True, **WIDE)
                st.markdown("**スコア間の順位相関（分析対象の区画）**")
                st.dataframe(d[["score_E56", "score_E55", "score_A_step5", "score_B_H1_step5"]].rename(columns={
                    "score_E56": "E56", "score_E55": "E55", "score_A_step5": "A", "score_B_H1_step5": "B"}).corr("spearman").round(3), **WIDE)
            with c2:
                sp = spots.dropna(subset=["E56スコア", "E55スコア（STEP5.5）"]).copy()
                sp = sp[sp["座標の確かさ"].str[0].isin(["A", "B"])].drop_duplicates("mesh_code")
                sp["カテゴリ区分"] = np.where(sp["カテゴリ"].isin(["トンネル", "橋"]), "トンネル・橋", "その他")
                st.altair_chart(alt.Chart(sp, title="既存スポットの区画：E55 と E56").mark_circle(size=22, opacity=0.6).encode(
                    x=alt.X("E55スコア（STEP5.5）:Q", title="E55（STEP 5.5）", scale=alt.Scale(domain=[0, 100])),
                    y=alt.Y("E56スコア:Q", title="E56（STEP 5.6）", scale=alt.Scale(domain=[0, 100])),
                    color=alt.Color("カテゴリ区分:N", scale=alt.Scale(domain=["その他", "トンネル・橋"], range=["#2a78d6", "#eb6834"])),
                    tooltip=["スポット名", "カテゴリ", alt.Tooltip("E55スコア（STEP5.5）:Q", format=".2f"), alt.Tooltip("E56スコア:Q", format=".2f")]).properties(height=380),
                    **WIDE)
                st.caption("具体的地点のある区画（同じ区画は1点）。トンネル・橋の区画は E56 で下がる傾向があります。")

