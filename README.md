# ghost-spot-map — E58正式版（STEP 5.8）

都県別ランキング上位30%の679件を採用した研究結果を表示するStreamlitアプリです。
起動ファイルは `app.py`。概要、研究詳細、2D、3D、ランキング・検索、データ出典を備えています。

## 起動

Python 3.13で動作確認済みです。

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

`.streamlit/secrets.toml` に `APP_PASSWORD = "自分で設定する閲覧パスワード"` を設定してください。
環境変数 `APP_PASSWORD` も利用できます。未設定時は結果を表示せず案内を出します。
本番パスワードはGitHubに登録しないでください（`.gitignore` 設定済み）。

## 研究結果の扱い

- 対象は東京・神奈川・埼玉・千葉・茨城・栃木・群馬・山梨。取得日2026-10-30。
- 2,252件から都県ごとにceil(N×0.30)件、計679件を採用。境界をまたぐ同点なし。
- E58はトンネル・橋だけの97区画等を学習から除外した結果。陽性210、評価31,183メッシュ。
- 全域31,303メッシュ内の順位点。保留739を含む32,042メッシュを表示。
- 11要因の寄与の合計は変換前の対数オッズ。E58の順位点や発生確率を足し合わせるものではありません。
- 住居33件の名称・住所・座標・サイトIDをE58表示用データに含めません。公開リスト646件、座標あり641件。
- 住居のメッシュ集計は26件分。残りは座標なし4件、対象区画外3件。
- 森林の除外重要度1.82（95%区間0.71〜3.01）。調整後は森林4〜6割で高い山型。
- 3Dの高さ・平滑化・集約は表示用で、地形や心霊体験の確率ではありません。

この公開用一式はE58正式版のみを含みます。旧17要因版・E56ページ・絞り込み前の順位データは含めていません。
E58表示用データには非採用スポットを含めていません。原報告書は「研究詳細」の参考資料から保存できます。

## 検証・データの再梱包

```sh
python -m unittest discover -s tests -v
python tools/build_e58_data.py /path/to/Metro_step5_8_ranking_top30_20261030
```

再梱包は既存のSTEP 5.8成果物を転記するだけで、学習やスコアの再計算は行いません。
`data/e58_provenance.json` に入力成果物のSHA-256を保存しています。
地図は表示用に0.001単位に丸め、表・CSVは元の数値を保持します。

## 公開

GitHubへの送信とStreamlit公開は未実施です。既存リポジトリのトップに、このフォルダの中身を反映してください。旧版の `pages/` フォルダは削除してください。
認証設定は[Streamlit公式ドキュメント](https://docs.streamlit.io/develop/concepts/connections/secrets-management)、
地図の埋め込みは[st.iframe](https://docs.streamlit.io/develop/api-reference/text/st.iframe)を参照してください。
