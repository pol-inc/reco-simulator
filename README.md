# reco-simulator

学生または募集の推薦リストを確認するための簡易シミュレータです。

![Reco Simulator screenshot](image.png)

## usage

```sh
uv sync
uv run run.py
```

## current behavior

- 学生・募集の検索は、半角空白と全角空白で区切った複数キーワードの AND 検索に対応しています。
- 検索結果カードでは、入力した各キーワードを個別にハイライトします。
- 学生の類似結果は引き続きダミーデータです。
- 募集の類似結果は実スコア計算を使用します。
- 募集の次のカラムは `scores_*.npy` を使わず、`,` 区切り値の部分一致で `0/1` スコアを付与します。
  - `recruit_name`
  - `company_name`
  - `research_fields`
  - `research_classifications`
  - `occupation`
  - `recruit_type_name`
  - `work_locations`
- Step 3 のスライダー一覧は広い画面で 2 段組、狭い画面で 1 段組になります。
