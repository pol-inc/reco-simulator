import json
import os
from rank_bm25 import BM25Okapi
import numpy as np
import pandas as pd
import requests

ES = "http://localhost:9200"  # ElasticSearch をローカル起動しておく
PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", "")

# recruit_id と company_id は数値 ID なので類似度計算から除外する
STOP_COLS_RECRUIT = {"recruit_id", "company_id"}

K = 50  # 各行で保持する上位件数


def tokenize(session, text):
    if not isinstance(text, str) or len(text) < 5:
        return []

    try:
        r = session.post(
            f"{ES}/_analyze",
            json={
                "tokenizer": "kuromoji_tokenizer",
                "filter": [
                    "kuromoji_baseform",
                    "kuromoji_part_of_speech",
                    "cjk_width",
                    "ja_stop",
                    "kuromoji_stemmer",
                    "lowercase",
                ],
                "text": text,
            },
            timeout=3,
        )
        r.raise_for_status()
        return [t["token"] for t in r.json()["tokens"]]
    except Exception as e:
        print(f"Error: {e}")
        return []


def scores(df, col, session, k=K):
    print(f"Processing col: {col}")

    n = len(df)
    k_actual = min(k, n)

    combined_items = df[col].fillna("").astype(str).tolist()
    corpus = [tokenize(session, text) for text in combined_items]
    bm25 = BM25Okapi(corpus)

    top_indices = np.empty((n, k_actual), dtype=np.int32)
    top_scores_arr = np.empty((n, k_actual), dtype=np.float32)

    for i in range(n):
        query = corpus[i]
        row_scores = bm25.get_scores(query)
        if k_actual < n:
            top_k_idx = np.argpartition(row_scores, -k_actual)[-k_actual:]
        else:
            top_k_idx = np.arange(n)
        sorted_idx = top_k_idx[np.argsort(row_scores[top_k_idx])[::-1]]
        top_indices[i] = sorted_idx.astype(np.int32)
        top_scores_arr[i] = row_scores[sorted_idx].astype(np.float32)

    np.save(f"data/scores_{col}_indices.npy", top_indices)
    np.save(f"data/scores_{col}_scores.npy", top_scores_arr)


if __name__ == "__main__":
    session = requests.Session()
    session.auth = ("elastic", PASSWORD)

    df = pd.read_csv("data/recruit_info.csv")
    meta = []
    for col in df.columns:
        if col in STOP_COLS_RECRUIT:
            continue
        scores(df, col, session, k=K)
        meta.append(col)

    id_map = df["recruit_id"].values
    np.save("data/scores_Recruit_id_map.npy", id_map)

    with open("data/scores_Recruit_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(meta)} column score files and metadata.")

