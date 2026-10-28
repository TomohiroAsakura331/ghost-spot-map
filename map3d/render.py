"""3D分析マップ（Three.js）のHTMLを組み立てる。

- 分析データ: data/map3d_data.json.gz（tools/build_map3d_data.py で既存CSV・レポートから抽出）
- three.js r160 + OrbitControls を同梱（map3d/vendor, MITライセンス）。外部CDNに依存しない。
- データは gzip のまま base64 で埋め込み、ブラウザの DecompressionStream で展開する。
"""
from __future__ import annotations

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).resolve().parent / "template.html"
VENDOR = Path(__file__).resolve().parent / "vendor" / "three_r160_bundle.min.js"
DATA = ROOT / "data" / "map3d_data.json.gz"


def build_map3d_html(data_path: Path = DATA) -> str:
    html = TEMPLATE.read_text(encoding="utf-8")
    three = VENDOR.read_text(encoding="utf-8").replace("</script", "<\\/script")
    b64 = base64.b64encode(Path(data_path).read_bytes()).decode("ascii")
    return html.replace("/*__THREE_BUNDLE__*/", three, 1).replace("__DATA_B64__", b64, 1)


if __name__ == "__main__":  # ローカル確認用: python -m map3d.render > preview.html
    import sys
    sys.stdout.write(build_map3d_html())
