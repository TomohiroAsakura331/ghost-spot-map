"""Package existing STEP 5.8 results for display; never train or recompute E58."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def build(source: Path, target: Path = ROOT):
    out = source / "outputs"
    data = target / "data"
    data.mkdir(parents=True, exist_ok=True)
    payload = json.loads(gzip.decompress((source / "map/data/s58_map_data.json.gz").read_bytes()))
    m, s, meta = payload["mesh"], payload["spots"], payload["meta"]
    keep = [i for i, adopted in enumerate(s["top30"]) if adopted]
    payload["spots"] = {key: [values[i] for i in keep] for key, values in s.items()}
    for key in ["e56", "l56", "rk56", "k56", "c56", "g56"]:
        del m[key]
    # The earlier listing label is irrelevant to the E58 release. Preserve only holdout status.
    m["g"] = [2 if v == 2 else 0 for v in m["g"]]
    del meta["nc56"]
    meta["source"] = "STEP 5.8（E58）正式版"
    meta["n_public_spots"] = len(keep)
    assert len(keep) == 646 and sum(x is not None for x in payload["spots"]["lat"]) == 641
    (data / "e58_map.json.gz").write_bytes(gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(), mtime=0))

    raw = pd.read_csv(out / "s58_mesh_scores_E58.csv", dtype={"mesh_code": str})
    columns = ["mesh_code", "primary_pref", "municipality", "inD", "stratum3", "score_E58", "E58_logit",
               "E58安定度_上位5パーセント", "E58の主な押し上げ要因"]
    columns += [c for c in raw if c.startswith("cE58_") or c.startswith("gE58_")]
    mesh = raw[columns].copy()
    mesh["rank_E58"] = m["rk58"]
    mesh["hidden_residences"] = m["hid"]
    mesh["n_top30"] = m["n30"]
    mesh.to_csv(data / "e58_mesh.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})

    a = pd.read_csv(out / "s58_adopted_top30_spots.csv", dtype={"1kmメッシュ": str})
    assert len(a) == 679 and a["スポットID（サイト）"].is_unique
    private = a["カテゴリ"].eq("住居")
    assert private.sum() == 33
    public = a.loc[~private, ["スポットID（サイト）", "スポット名", "都県", "市区町村", "カテゴリ", "都県内ランキング順位",
                              "都県内掲載総数", "上位割合（%）", "座標の確かさ", "緯度", "経度", "1kmメッシュ", "個別ページURL"]].copy()
    public["1kmメッシュ"] = public["1kmメッシュ"].str.replace(r"\.0$", "", regex=True)
    public = public.merge(mesh, left_on="1kmメッシュ", right_on="mesh_code", how="left", validate="m:1")
    public.to_csv(data / "e58_public_spots.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    adoption = pd.read_csv(out / "s58_adoption_by_prefecture.csv")
    adoption = adoption[adoption.pref.isin(meta['prefs'])]
    adoption[["pref", "掲載総数", "実際の採用件数", "座標あり", "座標なし", "広域の代表点", "既存に無い"]].rename(columns={"pref": "都県", "実際の採用件数": "採用件数", "既存に無い": "非表示の住居"}).to_csv(data / "e58_adoption.csv", index=False)
    importance = pd.read_csv(out / "s58_factor_importance_E56_vs_E58.csv")
    cols = ["要因", "E58_順位", "E58_悪化（万分の1）", "E58_95下", "E58_95上", "E58_悪化した組の割合（%）", "E58_判定"]
    importance[cols].sort_values("E58_順位").to_csv(data / "e58_importance.csv", index=False)
    quality = json.loads((source / "metadata/s58_quality_summary.json").read_text())
    (data / "e58_quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2))
    provenance = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [
        source / "map/data/s58_map_data.json.gz", out / "s58_mesh_scores_E58.csv",
        out / "s58_adopted_top30_spots.csv", out / "s58_factor_importance_E56_vs_E58.csv", out / "step5_8_report.html"]}
    (data / "e58_provenance.json").write_text(json.dumps({"release": "E58", "ranking_date": "2026-10-30", "source_sha256": provenance}, ensure_ascii=False, indent=2))
    print("Packaged E58: 32,042 meshes, 679 adopted (646 public rows, 33 private residences), 641 pins")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Existing Metro_step5_8_ranking_top30_20261030 directory")
    args = parser.parse_args()
    build(args.source)
