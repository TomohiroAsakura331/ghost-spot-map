"""STEP 5 地図（既存スポット順位・未登録の高スコア地域、deck.gl）のHTMLを組み立てる。

- データ: data/step5_map_data.json.gz（tools/build_step5_data.py で STEP 5 の成果物から作成）
- deck.gl 8.9.36 を同梱（step5map/vendor, MITライセンス）。外部CDNに依存しない。
- データは gzip のまま base64 で埋め込み、ブラウザの DecompressionStream で展開する（map3d と同じ方式）。
"""
from __future__ import annotations

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).resolve().parent / "template.html"
VENDOR = Path(__file__).resolve().parent / "vendor" / "deckgl_8.9.36.min.js"
DATA = ROOT / "data" / "step5_map_data.json.gz"


def build_step5_html(data_path: Path = DATA) -> str:
    html = TEMPLATE.read_text(encoding="utf-8")
    deck = VENDOR.read_text(encoding="utf-8").replace("</script", "<\\/script")
    b64 = base64.b64encode(Path(data_path).read_bytes()).decode("ascii")
    return html.replace("/*__DECK_BUNDLE__*/", deck, 1).replace("__DATA_B64__", b64, 1)


if __name__ == "__main__":  # ローカル確認用: python -m step5map.render > step5_preview.html
    import sys
    sys.stdout.write(build_step5_html())
