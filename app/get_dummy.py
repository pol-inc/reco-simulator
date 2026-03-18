import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CATEGORY_CONFIG = {
    "Student": {
        "path": BASE_DIR / "data" / "student_general.csv",
        "id_column": "account_id",
        "title_column": "summary",
    },
    "Recruit": {
        "path": BASE_DIR / "data" / "recruit_info.csv",
        "id_column": "recruit_id",
        "title_column": "recruit_name",
    },
}
STOP_LIST = {"account_id", "year", "sex", "recruit_id"}

_meta_cache: dict[str, list[str]] = {}
_topk_cache: dict[tuple, tuple] = {}


def _load_meta(category: str) -> dict:
    if category not in _meta_cache:
        meta_path = BASE_DIR / "data" / f"scores_{category}_meta.json"
        if not meta_path.exists():
            return {}
        with open(meta_path, encoding="utf-8") as f:
            _meta_cache[category] = json.load(f)
    return _meta_cache[category]


def _load_top_k(category: str, col_name: str) -> tuple:
    key = (category, col_name)
    if key not in _topk_cache:
        data_dir = BASE_DIR / "data"
        indices = np.load(str(data_dir / f"scores_{col_name}_indices.npy"))
        scores_arr = np.load(str(data_dir / f"scores_{col_name}_scores.npy"))
        _topk_cache[key] = (indices, scores_arr)
    return _topk_cache[key]


def _validate_category(category: str):
    if category not in CATEGORY_CONFIG:
        raise ValueError("category must be Student or Recruit")


def _to_native(value):
    if pd.isna(value):
        return ""
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return value
    return value


def _serialize_rows(df: pd.DataFrame, category: str):
    config = CATEGORY_CONFIG[category]
    id_column = config["id_column"]
    title_column = config["title_column"]
    records = []

    for _, row in df.iterrows():
        data = {col: _to_native(row[col]) for col in df.columns}
        records.append(
            {
                "id": str(_to_native(row.get(id_column, ""))),
                "primaryText": str(_to_native(row.get(title_column, ""))),
                "secondaryText": str(_to_native(row.get(id_column, ""))),
                "data": data,
            }
        )

    return records


def load_dataframe(category: str):
    _validate_category(category)
    csv_path = CATEGORY_CONFIG[category]["path"]
    return pd.read_csv(csv_path)


def get_columns(category: str):
    df = load_dataframe(category)
    return [col for col in df.columns.tolist() if not col.endswith("_id")]


def search_items(category: str, keyword: str, limit: int = 20):
    df = load_dataframe(category)
    config = CATEGORY_CONFIG[category]
    id_column = config["id_column"]
    keyword = (keyword or "").strip()

    if keyword:
        mask = (
            df.astype(str)
            .apply(
                lambda column: column.str.contains(
                    keyword, case=False, na=False, regex=False
                )
            )
            .any(axis=1)
        )
        results_df = df[mask]
        if len(results_df) > limit:
            results_df = results_df.sample(n=limit)
        results_df = results_df.sort_values(by=id_column, ascending=True)
    else:
        results_df = df.sort_values(by=id_column, ascending=True).head(limit)

    return _serialize_rows(results_df.head(limit), category)


def _normalize_column_specs(selected_columns: list, available_columns: list[str]):
    col_specs = []
    for item in selected_columns:
        if isinstance(item, dict):
            name = str(item.get("name", ""))
            weight = float(item.get("weight", 1.0))
        else:
            name = str(item)
            weight = 1.0

        if name not in available_columns:
            continue

        safe_weight = min(10.0, max(0.0, weight))
        if safe_weight <= 0.0:
            continue

        col_specs.append({"name": name, "weight": safe_weight})

    return col_specs


def get_similarity_dummy(
    category: str,
    selected_columns: list,
    selected_item_id: str | None = None,
    row_normalized: bool = False,
):
    _validate_category(category)

    df = load_dataframe(category)
    valid_col_specs = _normalize_column_specs(selected_columns, df.columns.tolist())

    if category == "Recruit":
        return _get_recruit_similarity(
            df,
            valid_col_specs,
            selected_item_id,
            row_normalized=row_normalized,
        )

    # Student: ダミー継続
    return _get_dummy_results(df, valid_col_specs, selected_item_id, category)


def _get_recruit_similarity(df, col_specs, selected_item_id, row_normalized=False):
    meta = _load_meta("Recruit")
    id_map_path = BASE_DIR / "data" / "scores_Recruit_id_map.npy"

    if not meta or not id_map_path.exists():
        return _get_dummy_results(df, col_specs, selected_item_id, "Recruit")

    id_map = np.load(str(id_map_path), allow_pickle=True)
    str_id_map = [str(x) for x in id_map]
    query_str = str(selected_item_id) if selected_item_id is not None else ""

    if query_str not in str_id_map:
        return []

    query_idx = str_id_map.index(query_str)

    config = CATEGORY_CONFIG["Recruit"]
    id_col = config["id_column"]
    title_col = config["title_column"]

    valid_specs = [cs for cs in col_specs if cs["name"] in meta]
    if not valid_specs:
        return []

    # agg_scores[row_idx][col_name] = weighted_score
    agg_scores: dict[int, dict[str, float]] = {}

    for cs in valid_specs:
        col_name = cs["name"]
        weight = cs["weight"]
        indices_arr, scores_arr = _load_top_k("Recruit", col_name)

        row_indices = indices_arr[query_idx]
        row_scores = scores_arr[query_idx].astype(np.float64)

        if row_normalized:
            row_sum = row_scores.sum()
            if row_sum > 0:
                row_scores = row_scores / row_sum

        for ridx, sc in zip(row_indices, row_scores):
            ridx = int(ridx)
            if ridx < 0:
                continue
            if ridx not in agg_scores:
                agg_scores[ridx] = {}
            agg_scores[ridx][col_name] = float(sc) * weight

    final_scores: dict[int, float] = {}
    for ridx, col_scores in agg_scores.items():
        if ridx == query_idx:
            continue
        final_scores[ridx] = sum(col_scores.values())

    sorted_items = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for ridx, sc in sorted_items[:20]:
        row = df.iloc[ridx]
        row_data = {col: _to_native(row[col]) for col in df.columns}
        selected_values = {cs["name"]: row_data.get(cs["name"], "") for cs in col_specs}
        results.append(
            {
                "id": str(row_data.get(id_col, "")),
                "primaryText": str(row_data.get(title_col, "")),
                "secondaryText": str(row_data.get(id_col, "")),
                "selectedValues": selected_values,
                "score": round(sc, 4),
                "method": "WeightedSum",
                "data": row_data,
            }
        )

    return results


def _get_dummy_results(df, col_specs, selected_item_id, category):
    config = CATEGORY_CONFIG[category]
    id_column = config["id_column"]
    title_column = config["title_column"]
    base_offset = sum(ord(ch) for ch in str(selected_item_id or "")) % 7

    candidates = df.iloc[10:20]
    items = []

    for rank, (_, row) in enumerate(candidates.iterrows(), start=1):
        row_data = {col: _to_native(row[col]) for col in df.columns}
        selected_values = {cs["name"]: row_data.get(cs["name"], "") for cs in col_specs}
        n_cols = len(col_specs)
        score = round(max(0.0, 96.0 - rank * 3.1 - n_cols - base_offset), 2)

        items.append(
            {
                "id": str(row_data.get(id_column, "")),
                "primaryText": str(row_data.get(title_column, "")),
                "secondaryText": str(row_data.get(id_column, "")),
                "selectedValues": selected_values,
                "score": score,
                "method": "Dummy",
                "data": row_data,
            }
        )

    return items


if __name__ == "__main__":
    print(CATEGORY_CONFIG)
