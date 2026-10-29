# 既存スポット順位・未登録候補タブの追加（ghost-spot-map / STEP 5）

## 追加・変更するファイル

```
ghost-spot-map/
├─ app.py                               ← 変更（3つ目のタブを追加。既存の2D/3Dタブ・パスワード認証は変更なし）
├─ step5map/                            ← 追加
│  ├─ __init__.py
│  ├─ render.py                         … 地図HTMLの組み立て（map3d/render.py と同じ方式）
│  ├─ template.html                     … 地図本体（deck.gl）
│  └─ vendor/
│     ├─ deckgl_8.9.36.min.js           … deck.gl 8.9.36（MIT, 同梱。CDN不要）
│     └─ DECKGL_LICENSE.txt
├─ data/
│  ├─ step5_map_data.json.gz            ← 追加（約1.5MB。地図用データ）
│  ├─ step5_existing_spots_ranking.csv  ← 追加（約1.5MB。表・CSV保存用）
│  └─ step5_unregistered_candidates.csv ← 追加（約0.5MB）
└─ tools/
   └─ build_step5_data.py               ← 追加（データ再生成の記録。アプリ実行時には使わない）
```

## 必要なライブラリ

- 追加なし。`pandas` は streamlit の依存関係として入ります（`st.column_config.LinkColumn` を使うため streamlit 1.23 以上）。
- 地図はブラウザの DecompressionStream で gzip を展開します（3D分析マップと同じ。Chrome / Edge / Firefox 113以降 / Safari 16.4以降）。

## 反映方法

1. 上記ファイルをリポジトリに追加し、`app.py` を置き換えて `main` に push
2. Streamlit Community Cloud が自動で再デプロイ（反映されない場合は「Reboot app」）
3. Secrets（`APP_PASSWORD`）は変更不要。新しいタブも既存の `check_password()` の後に表示されます。

## タブの内容

- 地図（2D／3D切り替え）：A 掲載傾向／A 基準モデル／B 立地条件（H1）の切り替え、都県・市区町村の絞り込み、
  未登録の高スコア地域（①全域A上位1%、②都県内A上位1%、③参考B上位1%）、既存スポット（具体的地点・広域代表点）、
  地図右上の順位一覧・候補一覧、クリックで要因情報と注意点。
- 表：既存スポットの順位、未登録の高スコア地域（都県・市区町村で絞り込み、CSV保存）。

## 表示上の約束

- A＝STEP 3/4 の空間交差検証で検証したロジスティック回帰の掲載傾向（順位0–100）、B＝H1（仮説の向き・等重み）。AとBは混ぜていません。
- どちらも心霊体験の発生確率ではありません。未登録は「心霊スポットがない」ことを意味しません。
- 柱の高さ＝スコアの3乗×倍率（見やすさのため）。

## 分析結果を更新したとき

STEP 5 の解析フォルダ（`Metro_step5_ranking_candidates_20261029/scripts`）で各スクリプトを実行し、
`step5_export_app.py`（＝ `tools/build_step5_data.py`）で `step5map/` と `data/step5_*` を作り直してコミットします。

## 注意

- リポジトリが公開設定の場合、`data/` のファイルは誰でも取得できます（既存の `composite_report.html` や `map3d_data.json.gz` と同様）。アプリのパスワードはデータファイル自体は保護しません。
- 背景地図（地理院タイル）は閲覧者のブラウザがインターネットから取得します。取得できなくても分析データの表示には影響しません。
