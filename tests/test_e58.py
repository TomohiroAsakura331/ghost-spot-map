import gzip
import json
import math
from pathlib import Path
import sys
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s58viz.data import filter_table, read_table
from s58viz.render import build, filter_payload


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(gzip.decompress((ROOT / 'data/e58_map.json.gz').read_bytes()))
        cls.mesh = read_table('e58_mesh.csv.gz')
        cls.spots = read_table('e58_public_spots.csv.gz')

    def test_counts_and_selection(self):
        adoption = read_table('e58_adoption.csv')
        self.assertEqual(len(self.mesh), 32042)
        self.assertEqual(int(self.mesh.inD.sum()), 31303)
        self.assertEqual(len(self.spots), 646)
        self.assertEqual(int(self.spots['緯度'].notna().sum()), 641)
        self.assertEqual(int(adoption['採用件数'].sum()), 679)
        self.assertEqual(int(adoption['非表示の住居'].sum()), 33)
        for _, r in adoption.iterrows():
            self.assertEqual(r['採用件数'], math.ceil(r['掲載総数'] * .30))
        self.assertTrue(self.spots['スポットID（サイト）'].is_unique)
        self.assertTrue((self.spots['都県内ランキング順位'] <= self.spots['都県内掲載総数'].apply(lambda n: math.ceil(n * .30))).all())

    def test_only_e58_and_public_adopted_data(self):
        m, s = self.payload['mesh'], self.payload['spots']
        self.assertEqual(len(s['name']), 646)
        self.assertEqual(set(s['top30']), {1})
        self.assertNotIn('住居', set(self.spots['カテゴリ']))
        self.assertFalse(any('56' in key for key in m))
        self.assertFalse(any('56' in key for key in self.mesh.columns))
        self.assertEqual(sum(m['hid']), 26)  # Four have no coordinates; three fall outside the analysis mesh set.

    def test_contributions_and_display_precision(self):
        total = self.mesh[[c for c in self.mesh if c.startswith('cE58_')]].sum(axis=1)
        self.assertLess(float((total - self.mesh.E58_logit).abs().max()), 1e-10)
        display = pd.Series(self.payload['mesh']['e58']) / 1000
        self.assertLessEqual(float((display - self.mesh.score_E58).abs().max()), .000501)
        self.assertTrue(self.mesh.score_E58.between(0, 100).all())
        self.assertTrue(self.mesh.loc[~self.mesh.inD, 'rank_E58'].isna().all())

    def test_filters_and_literal_search(self):
        t = filter_table(self.spots, '東京都', public=True)
        self.assertEqual(len(t), 146)
        self.assertEqual(set(t['都県']), {'東京都'})
        self.assertEqual(len(filter_table(self.spots, query='[', public=True)), 0)
        self.assertEqual(len(filter_table(self.spots, query='存在しない文字列', public=True)), 0)
        self.assertTrue(filter_table(self.mesh, score_min=99).score_E58.ge(99).all())
        self.assertTrue(filter_table(self.mesh, include_reference=False).inD.all())
        p = filter_payload(self.payload, '東京都')
        self.assertEqual(set(p['mesh']['pref']), {0})
        self.assertEqual(set(p['spots']['pref']), {'東京都'})
        self.assertEqual(len(p['mesh']['c58'][0]), len(p['mesh']['code']))
        self.assertEqual(len(p['mesh']['g58'][0]), len(p['mesh']['code']))

    def test_map_documents(self):
        for kind in ['2d', '3d']:
            for pref in ['すべて', '東京都']:
                html = build(kind, pref)
                self.assertNotIn('__DATA_B64__', html)
                template = (ROOT/f's58viz/template_{kind}.html').read_text()
                self.assertFalse('E56' in template)
                self.assertNotIn('全スポット', html)
                self.assertIn('DecompressionStream', html)


class AppTests(unittest.TestCase):
    def app(self):
        app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=40)
        app.secrets['APP_PASSWORD'] = '試験用E58'
        return app

    def test_missing_password_stops_without_results(self):
        app = AppTest.from_file(str(ROOT/'app.py')).run()
        self.assertFalse(app.exception)
        self.assertIn('未設定', app.error[0].value)
        self.assertFalse(app.sidebar.radio)

    def test_login_failure_success_and_logout(self):
        app = self.app().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.sidebar.radio)
        app.text_input[0].set_value('wrong')
        app.button[0].click().run()
        self.assertIn('パスワードが違います', app.error[0].value)
        app.text_input[0].set_value('試験用E58')
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state['authenticated'])
        app.sidebar.button[0].click().run()
        self.assertFalse(app.sidebar.radio)

    def test_all_pages_filters_and_empty_search(self):
        app = self.app()
        app.session_state['authenticated'] = True
        app.run()
        for page in ['研究詳細', '2D E58マップ', '3D E58マップ', 'ランキング・検索', 'データ出典']:
            app.sidebar.radio[0].set_value(page).run()
            self.assertFalse(app.exception, str(app.exception))
        app.sidebar.radio[0].set_value('ランキング・検索').run()
        app.sidebar.selectbox[0].set_value('東京都').run()
        app.text_input[0].set_value('存在しない文字列').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value), 0)
        app.text_input[0].set_value('').run()
        self.assertFalse(app.exception)
        next(r for r in app.radio if r.label == '表示対象').set_value('メッシュ').run()
        self.assertFalse(app.exception)
        self.assertGreater(len(app.dataframe[0].value), 0)


if __name__ == '__main__':
    unittest.main()
