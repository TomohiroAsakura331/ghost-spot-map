from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PREFS = ["東京都", "神奈川県", "埼玉県", "千葉県", "茨城県", "栃木県", "群馬県", "山梨県"]


def read_table(name):
    return pd.read_csv(ROOT / "data" / name, dtype={"mesh_code": str, "1kmメッシュ": str})


def filter_table(table, prefecture="すべて", municipality="すべて", query="", score_min=0, public=False, include_reference=True):
    result = table.copy()
    pref, muni = ("都県", "市区町村") if public else ("primary_pref", "municipality")
    if prefecture != "すべて":
        result = result[result[pref].eq(prefecture)]
    if municipality != "すべて":
        result = result[result[muni].eq(municipality)]
    if query.strip():
        columns = ["スポット名", "都県", "市区町村", "1kmメッシュ"] if public else ["mesh_code", "primary_pref", "municipality"]
        mask = pd.Series(False, index=result.index)
        for col in columns:
            mask |= result[col].fillna("").astype(str).str.contains(query.strip(), case=False, regex=False)
        result = result[mask]
    if score_min > 0:
        result = result[result.score_E58.ge(score_min)]
    if not include_reference:
        result = result[result.inD.eq(True)]
    return result
