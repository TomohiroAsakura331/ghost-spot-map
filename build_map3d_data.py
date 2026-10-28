"""3D分析マップ用データを既存の分析結果から抽出する（スコアの再計算はしない）。

入力
  - mesh_composite.csv      : 既存分析の全1kmメッシュ総合評価CSV
  - composite_report.html   : 既存レポート（<script id="spots-data"> 内の掲載スポットJSON）
出力
  - data/map3d_data.json.gz : 3D地図が読み込む軽量データ

方針
  - score_H1/H2/H3・rank_H1/H2/H3・群値・寄与・順位の不確実性は CSV / JSON の値をそのまま転記する。
    数値の丸めは表示用に小数3桁（レポートの表示桁）にそろえるのみ。
  - 主順位対象（main_eligible=True）以外のメッシュには順位を付けない。
  - 掲載スポットは composite_rank_eligible=True の616件のみ spot_rank_* を持つ（既存値）。

使い方
  python tools/build_map3d_data.py --csv path/to/mesh_composite.csv \
      --report composite_report.html --out data/map3d_data.json.gz
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
from datetime import date
from pathlib import Path

import pandas as pd

EXCLUSION_JA = {
    "ok": "主順位対象",
    "required_values_missing": "11必須指標のいずれかが欠損（総合点なし）",
    "quality50_condition_not_met": "既存fit_quality50条件外（参考点のみ・主順位なし）",
    "quality50_sensitivity_condition_not_met": "既存fit_quality50条件外（参考点のみ・主順位なし）",
    "broad_place_reference_pin": "広域地名の代表ピン（範囲未確認）",
    "within_100m_mesh_boundary_sensitivity_band": "メッシュ境界から100m以内（境界感度帯）",
    "no_usable_coordinates": "利用可能な座標なし",
    "outside_admin_geometry": "行政区域の範囲外",
    "source_pref_coordinate_disagree": "掲載都県と座標の所在都県が不一致",
    "outside_existing_mesh": "既存メッシュの範囲外",
}
POINT_ROLE_JA = {
    "source_published_feature_pin": "掲載地物のピン",
    "broad_place_representative_pin_extent_unverified": "広域地名の代表ピン（範囲未確認）",
    "unresolved_anonymized_name": "匿名・未特定の掲載名",
}


def r3(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return round(f, 3)


def ri(v):
    f = r3(v)
    return None if f is None else int(round(f))


def mesh_row_col(code: str):
    """3次メッシュ(8桁)→南西隅を原点とする整数格子 (row: 緯度方向 30秒, col: 経度方向 45秒)。"""
    p, q, r, s, t, u = int(code[0:2]), int(code[2:4]), int(code[4]), int(code[5]), int(code[6]), int(code[7])
    return p * 80 + r * 10 + t, q * 80 + s * 10 + u


def load_spots(report_path: Path):
    html = report_path.read_text(encoding="utf-8")
    m = re.search(r'<script id="spots-data" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise SystemExit("composite_report.html に spots-data が見つかりません")
    return json.loads(m.group(1))


def build(csv_path: Path, report_path: Path):
    use = [
        "mesh_code", "primary_pref", "fit_domain", "center_location", "main_eligible", "main_exclusion",
        "score_H1", "score_H2", "score_H3", "rank_H1", "rank_H2", "rank_H3", "rank_within_domain",
        "group_context", "group_cemetery", "group_water", "group_transport",
        "weight_rank_best", "weight_rank_worst", "structure_rank_best", "structure_rank_worst",
        "direction_rank_best", "direction_rank_worst",
    ]
    df = pd.read_csv(csv_path, encoding="utf-8-sig", usecols=use, dtype={"mesh_code": str}, low_memory=False)

    prefs = sorted(df["primary_pref"].dropna().unique().tolist())
    locs = sorted(df["center_location"].dropna().unique().tolist())
    pref_ix = {p: i for i, p in enumerate(prefs)}
    loc_ix = {p: i for i, p in enumerate(locs)}
    excl = ["ok", "required_values_missing", "quality50_condition_not_met"]
    unknown = set(df["main_exclusion"].dropna()) - set(excl)
    if unknown:
        raise SystemExit(f"未知の main_exclusion: {unknown}")

    rc = [mesh_row_col(c) for c in df["mesh_code"]]
    m = {
        "code": df["mesh_code"].astype(int).tolist(),
        "row": [a for a, _ in rc],
        "col": [b for _, b in rc],
        "pref": [pref_ix.get(p, -1) if isinstance(p, str) else -1 for p in df["primary_pref"]],
        "loc": [loc_ix.get(p, -1) if isinstance(p, str) else -1 for p in df["center_location"]],
        "dom": [0 if d == "本土" else 1 for d in df["fit_domain"]],
        "ex": [excl.index(e) for e in df["main_exclusion"]],
    }
    for k in ["score_H1", "score_H2", "score_H3", "group_context", "group_cemetery", "group_water", "group_transport"]:
        m[k] = [r3(v) for v in df[k]]
    for k in ["rank_H1", "rank_H2", "rank_H3", "rank_within_domain", "weight_rank_best", "weight_rank_worst",
              "structure_rank_best", "structure_rank_worst", "direction_rank_best", "direction_rank_worst"]:
        m[k] = [ri(v) for v in df[k]]

    # 主順位外のメッシュに順位が混入していないことを確認
    elig = df["main_eligible"] == True  # noqa: E712
    assert df.loc[~elig, ["rank_H1", "rank_H2", "rank_H3"]].isna().all().all(), "主順位外に順位あり"
    n_ranked = int(elig.sum())

    raw_spots = load_spots(report_path)
    spots = []
    for x in raw_spots:
        reasons = (x.get("composite_exclusion") or "").split(";")
        spots.append({
            "id": x["spot_id"], "name": x["name"], "pref": x.get("source_pref"), "addr": x.get("address"),
            "lat": x.get("latitude"), "lon": x.get("longitude"), "url": x.get("source_url"),
            "mesh": x.get("mesh_code"), "loc": x.get("center_location"),
            "role": POINT_ROLE_JA.get(x.get("point_role"), x.get("point_role")),
            "ranked": bool(x.get("composite_rank_eligible")),
            "reason": [EXCLUSION_JA.get(r, r) for r in reasons if r],
            "s": [r3(x.get(f"score_H{i}")) for i in (1, 2, 3)],
            "sr": [ri(x.get(f"spot_rank_H{i}")) for i in (1, 2, 3)],
            "mr": [ri(x.get(f"rank_H{i}")) for i in (1, 2, 3)],
            "g": [r3(x.get(k)) for k in ("group_context", "group_cemetery", "group_water", "group_transport")],
            "wb": ri(x.get("spot_weight_rank_best")), "ww": ri(x.get("spot_weight_rank_worst")),
            "ex": x.get("H1_explanation"),
        })
        if not spots[-1]["ranked"]:
            assert all(v is None for v in spots[-1]["sr"]), "主順位外スポットに順位あり"
    n_spot_ranked = sum(s["ranked"] for s in spots)

    meta = {
        "built": date.today().isoformat(),
        "source": {"mesh_csv": csv_path.name, "report": report_path.name},
        "title": "首都圏・総合環境適合度（1都7県・東京都島しょ）",
        "mesh_n": len(df), "ranked_n": n_ranked,
        "spot_n": len(spots), "spot_ranked_n": n_spot_ranked,
        "spot_no_coord_n": sum(1 for s in spots if s["lat"] is None or s["lon"] is None),
        "prefs": prefs, "locs": locs,
        "exclusion": [EXCLUSION_JA[e] for e in excl],
        # 上位帯：レポートの upper_thresholds（比較集合32,082・名目上限 321/1605/3209、同順位を含む）
        "upper": [{"pct": 1, "ceiling": 321}, {"pct": 5, "ceiling": 1605}, {"pct": 10, "ceiling": 3209}],
        "scenarios": {
            "H1": {"label": "H1 参考主設定",
                   "desc": "G1地形・森林・寒冷／遠隔、G2掲載墓地への近接、G3掲載水域への近接、G4橋・高架またはトンネル近接の4群を各25%で平均（H1=(G1+G2+G3+G4)/4）。高地・急傾斜・森林・寒冷・遮蔽・遠隔ほど高い方向。"},
            "H2": {"label": "H2 対立設定（方向反転）",
                   "desc": "H1と同じ4群・同じ重みで、G1地形・森林・寒冷／遠隔群の評価方向だけを反転（低地・緩傾斜・市街地寄り・近接ほど高い）。"},
            "H3": {"label": "H3 対立設定（G1除外）",
                   "desc": "方向が競合するG1地形・森林・寒冷／遠隔群を除外し、G2墓地・G3水域・G4橋／トンネルの3群で評価。"},
        },
        "groups": ["G1 地形・森林・寒冷／遠隔", "G2 掲載墓地への近接", "G3 掲載水域への近接", "G4 橋・高架またはトンネル近接"],
    }
    return {"meta": meta, "mesh": m, "spots": spots}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--out", default=Path("data/map3d_data.json.gz"), type=Path)
    a = ap.parse_args()
    data = build(a.csv, a.report)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with gzip.open(a.out, "wb", compresslevel=9) as f:
        f.write(raw)
    md = data["meta"]
    print(f"meshes={md['mesh_n']} ranked={md['ranked_n']} spots={md['spot_n']} spot_ranked={md['spot_ranked_n']} "
          f"json={len(raw)/1e6:.2f}MB gz={a.out.stat().st_size/1e6:.2f}MB -> {a.out}")


if __name__ == "__main__":
    main()
