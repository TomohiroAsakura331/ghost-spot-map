# -*- coding: utf-8 -*-
"""ghost-spot-map（Streamlit）へ組み込む STEP 5 のファイル一式を作る。
既存の map3d と同じ方式：ライブラリ（deck.gl）を同梱し、データは gzip のまま base64 で HTML に埋め込み、
ブラウザの DecompressionStream で展開する。出力先：<OUT>/app_integration/ghost-spot-map/"""
import os, sys, json, gzip, shutil
sys.path.insert(0, os.path.dirname(__file__))
import step5_build_map as B   # データ（data, spots, cands, L, bnd, facts）とHTMLテンプレートを再利用
from step5_common import P

R = f"{P['OUT']}/app_integration/ghost-spot-map"
for d in ('step5map/vendor', 'data', 'tools'):
    os.makedirs(f'{R}/{d}', exist_ok=True)

# 1) データ（gzip JSON）
payload = dict(data=B.data, spots=B.spots, cands=B.cands, lookup=B.L, bnd=B.bnd, facts=B.facts)
import math
def _clean(x):
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)): return None
    if isinstance(x, dict): return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [_clean(v) for v in x]
    return x
raw = json.dumps(_clean(payload), ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
with gzip.open(f'{R}/data/step5_map_data.json.gz', 'wb', compresslevel=9) as f:
    f.write(raw)

# 2) テンプレート（データ読み込みを gzip+base64 に置き換え）
T = B.HTML
T = T.replace('<script>__DECK__</script>', '<script>/*__DECK_BUNDLE__*/</script>', 1)
old = 'const D=__DATA__,S=__SPOTS__,CA=__CANDS__,L=__LOOKUP__,B=__BND__,F=__FACTS__;'
new = ('const DATA_B64="__DATA_B64__";\n(async function main(){\n'
       'async function loadData(){const bin=Uint8Array.from(atob(DATA_B64),c=>c.charCodeAt(0));'
       'const stream=new Blob([bin]).stream().pipeThrough(new DecompressionStream("gzip"));return await new Response(stream).json();}\n'
       'let P;try{P=await loadData();}catch(e){document.body.insertAdjacentHTML("beforeend",'
       '`<div style="position:absolute;top:40%;left:0;right:0;text-align:center">データを読み込めませんでした（ブラウザがgzip展開に未対応の可能性）：${e}</div>`);return;}\n'
       'const D=P.data,S=P.spots,CA=P.cands,L=P.lookup,B=P.bnd,F=P.facts;')
assert old in T; T = T.replace(old, new, 1)
assert T.rstrip().endswith('fillMuni();render();\n</script></body></html>')
T = T.replace('fillMuni();render();\n</script></body></html>', 'fillMuni();render();\n})();\n</script></body></html>')
open(f'{R}/step5map/template.html', 'w', encoding='utf-8').write(T)

# 3) deck.gl 同梱（MIT）
shutil.copy(B.DECK, f'{R}/step5map/vendor/deckgl_8.9.36.min.js')
open(f'{R}/step5map/vendor/DECKGL_LICENSE.txt', 'w').write("""deck.gl 8.9.36 (https://github.com/visgl/deck.gl) — MIT License

Copyright (c) 2015 - 2017 Uber Technologies, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
""")
open(f'{R}/step5map/__init__.py', 'w').write('')
open(f'{R}/step5map/render.py', 'w', encoding='utf-8').write('''"""STEP 5 地図（既存スポット順位・未登録の高スコア地域、deck.gl）のHTMLを組み立てる。

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
    deck = VENDOR.read_text(encoding="utf-8").replace("</script", "<\\\\/script")
    b64 = base64.b64encode(Path(data_path).read_bytes()).decode("ascii")
    return html.replace("/*__DECK_BUNDLE__*/", deck, 1).replace("__DATA_B64__", b64, 1)


if __name__ == "__main__":  # ローカル確認用: python -m step5map.render > step5_preview.html
    import sys
    sys.stdout.write(build_step5_html())
''')

# 4) 表データ（アプリの表・ダウンロード用）
cols_s = ['rank_A', 'rank_A_best_of_3splits', 'rank_A_worst_of_3splits', 'rank_B', 'spot_id', 'name', 'genre', 'spot_type', 'address',
          'primary_pref', 'municipality', 'lat', 'lon', 'mesh_code', 'score_A_listing_tendency', 'score_A_baseline_model', 'A_neighbourhood_mean',
          'score_B_H1_location', 'score_B_low_under_45_weight_sets', 'score_B_high_under_45_weight_sets', 'main_factors_A', 'lowering_factors_A',
          'main_factors_B', 'auxiliary_records', 'caveats', 'source_url']
import pandas as pd
s = pd.read_csv(f"{P['OUT']}/outputs/existing_spots_ranking.csv", dtype={'mesh_code': str})
s[cols_s].to_csv(f'{R}/data/step5_existing_spots_ranking.csv', index=False, encoding='utf-8')
c = pd.read_csv(f"{P['OUT']}/outputs/unregistered_candidates_ranking.csv", dtype={'peak_mesh': str})
c.to_csv(f'{R}/data/step5_unregistered_candidates.csv', index=False, encoding='utf-8')
shutil.copy(__file__, f'{R}/tools/build_step5_data.py')
print('json raw', len(raw), 'gz', os.path.getsize(f'{R}/data/step5_map_data.json.gz'))
