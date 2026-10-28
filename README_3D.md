# 3D分析マップの追加（ghost-spot-map）

## 追加・変更するファイル

```
ghost-spot-map/
├─ app.py                         ← 変更（2D/3Dタブ化。パスワード認証は従来のまま）
├─ composite_report.html          ← 変更なし（2D分析マップ）
├─ map3d/                         ← 追加
│  ├─ __init__.py
│  ├─ render.py                   … 3D地図HTMLの組み立て
│  ├─ template.html               … 3D地図本体（Three.js）
│  └─ vendor/
│     ├─ three_r160_bundle.min.js … three.js r160 + OrbitControls（MIT, 同梱）
│     └─ THREE_LICENSE.txt
├─ data/
│  └─ map3d_data.json.gz          ← 追加（約1.8MB。既存分析から抽出した表示用データ）
└─ tools/
   └─ build_map3d_data.py         ← 追加（データ再生成用。アプリ実行時には使わない）
```

## 必要なライブラリ

- アプリ実行時：**追加なし**（`streamlit` のみ。three.js は同梱しているためCDN不要）
- データ再生成時のみ：`pandas`（ローカルで実行）

`requirements.txt` は変更不要です。

## Streamlit Community Cloud への反映

1. 上記ファイルをリポジトリに追加・上書きし、コミットして `main` に push
2. Community Cloud が自動で再デプロイ（反映されない場合は管理画面の「Reboot app」）
3. Secrets（`APP_PASSWORD`）は従来どおり Cloud 管理画面の Settings → Secrets に置いたまま。
   コードやリポジトリには書かない。ローカル用 `.streamlit/secrets.toml` は `.gitignore` に入れておく：

```
.streamlit/secrets.toml
```

## 分析結果を更新したとき

`mesh_composite.csv` と `composite_report.html` を更新したら、ローカルで次を実行して `data/map3d_data.json.gz` を作り直し、コミットします。

```
python tools/build_map3d_data.py --csv path/to/mesh_composite.csv --report composite_report.html --out data/map3d_data.json.gz
```

スコア・順位・群値はCSV／レポートの値を小数3桁で転記するだけで、再計算はしていません。

## データの扱い（3D地図の表示ルール）

| 種類 | 件数 | 3D表示 |
|---|---|---|
| 主順位対象メッシュ（`main_eligible=True`） | 32,082 | スコアに応じて隆起・色分け |
| 必須指標の欠損（`required_values_missing`） | 4,543 | 高さ0の暗い灰色（0点とは別扱い） |
| 品質条件外（`quality50_condition_not_met`） | 305 | 高さ0の明るい灰色（参考点。主順位なし） |
| 掲載スポット（主順位対象） | 616 | 白ピン（各評価条件のTOP10はピンク） |
| 掲載スポット（主順位外） | 1,518 | 「主順位外も表示」で紫ピン。理由をツールチップに表示 |
| 座標なしスポット | 16 | 地図に表示できない（検索結果には出る） |

- 高さ ＝ (スコア/100)^強調 × 倍率。表示だけを変えるもので、スコア・順位は変わりません。
- 連続サーフェスは、隣り合う主順位対象メッシュの値だけを平均して滑らかにしています。データのないメッシュや海域へは値を広げません（外周は側壁で地面に下ろしています）。
- 「メッシュ柱」表示に切り替えると、平滑化なしの各メッシュの値そのものを確認できます。
- 上位帯の色分けは、レポートの upper_thresholds（比較集合32,082・名目上限321/1,605/3,209、同順位を含む）に従っています。

## 注意

- 背景地図（CARTO暗色／地理院タイル淡色）は閲覧者のブラウザがインターネットから取得します。取得できない場合も分析データの表示には影響しません。
- ブラウザは Chrome / Edge / Firefox 113以降 / Safari 16.4以降を想定しています（gzip展開に DecompressionStream を使用）。
- リポジトリが公開設定の場合、`data/map3d_data.json.gz` は（既存の `composite_report.html` と同様に）誰でも取得できます。アプリのパスワードはデータファイル自体は保護しません。
