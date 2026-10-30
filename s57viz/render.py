"""STEP 5.7 地図HTMLの組み立て（2D：deck.gl 8.9.36、3D：three.js r160）。

- 共通データ: data/s57_map_data.json.gz（scripts/s57_01_build_data.py で STEP 5.6 の成果物から転記して作成）
- ライブラリは s57viz/vendor に同梱（MITライセンス）。外部CDNに依存しない（背景地図タイルのみインターネットから取得）。
- データは gzip のまま base64 で埋め込み、ブラウザの DecompressionStream で展開する（ghost-spot-map の map3d・step5map と同じ方式）。
"""
from __future__ import annotations

import base64
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data" / "s57_map_data.json.gz"
DECK = HERE / "vendor" / "deckgl_8.9.36.min.js"
THREE = HERE / "vendor" / "three_r160_bundle.min.js"


def _b64(path: Path) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def build_2d_html(data_path: Path = DATA) -> str:
    html = (HERE / "template_2d.html").read_text(encoding="utf-8")
    lib = DECK.read_text(encoding="utf-8").replace("</script", "<\\/script")
    return html.replace("/*__DECK_BUNDLE__*/", lib, 1).replace("__DATA_B64__", _b64(data_path), 1)


def build_3d_html(data_path: Path = DATA) -> str:
    html = (HERE / "template_3d.html").read_text(encoding="utf-8")
    lib = THREE.read_text(encoding="utf-8").replace("</script", "<\\/script")
    return html.replace("/*__THREE_BUNDLE__*/", lib, 1).replace("__DATA_B64__", _b64(data_path), 1)


if __name__ == "__main__":  # 単独のHTMLとして書き出す: python -m s57viz.render 出力フォルダ
    import sys
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    (out / "s57_2d_map.html").write_text(build_2d_html(), encoding="utf-8")
    (out / "s57_3d_map.html").write_text(build_3d_html(), encoding="utf-8")
    print("written", out)
