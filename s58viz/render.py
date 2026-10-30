"""Build self-contained E58 map documents with bundled JavaScript libraries."""
import base64
import copy
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data/e58_map.json.gz"


def filter_payload(payload, prefecture="すべて"):
    result = copy.deepcopy(payload)
    if prefecture == "すべて":
        return result
    pi = result["meta"]["prefs"].index(prefecture)
    mesh = result["mesh"]
    indices = [i for i, p in enumerate(mesh["pref"]) if p == pi]
    for key, values in mesh.items():
        mesh[key] = [[row[i] for i in indices] for row in values] if key in {"c58", "g58"} else [values[i] for i in indices]
    spots = result["spots"]
    indices = [i for i, p in enumerate(spots["pref"]) if p == prefecture]
    result["spots"] = {k: [v[i] for i in indices] for k, v in spots.items()}
    result["bnd"]["features"] = [f for f in result["bnd"]["features"] if prefecture in json.dumps(f.get("properties", {}), ensure_ascii=False)]
    return result


def build(kind="2d", prefecture="すべて", data_path=DATA):
    if kind not in {"2d", "3d"}:
        raise ValueError("Map kind must be 2d or 3d")
    payload = filter_payload(json.loads(gzip.decompress(Path(data_path).read_bytes())), prefecture)
    if not payload["mesh"]["code"]:
        raise ValueError("選択した都県のメッシュデータがありません")
    packed = gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(), mtime=0)
    library, marker = ("deckgl_8.9.36.min.js", "/*__DECK_BUNDLE__*/") if kind == "2d" else ("three_r160_bundle.min.js", "/*__THREE_BUNDLE__*/")
    script = (HERE / "vendor" / library).read_text().replace("</script", "<\\/script")
    return (HERE / f"template_{kind}.html").read_text().replace(marker, script, 1).replace("__DATA_B64__", base64.b64encode(packed).decode(), 1)
