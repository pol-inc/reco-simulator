import re
from pathlib import Path

import pandas as pd

from app.get_score import get_recruit_column_definitions

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
    columns = [col for col in df.columns.tolist() if not col.endswith("_id")]
    if category == "Recruit":
        return get_recruit_column_definitions(columns)

    return [
        {
            "name": column,
            "label": column,
            "min": 0,
            "max": 10,
            "step": 0.1,
            "defaultWeight": 1,
            "matchType": "score",
        }
        for column in columns
    ]


def _parse_search_terms(keyword: str) -> list[str]:
    return [term for term in re.split(r"[\s\u3000]+", (keyword or "").strip()) if term]


def search_items(category: str, keyword: str, limit: int = 20):
    df = load_dataframe(category)
    config = CATEGORY_CONFIG[category]
    id_column = config["id_column"]
    search_terms = _parse_search_terms(keyword)

    if search_terms:
        as_text = df.astype(str)
        mask = pd.Series(True, index=df.index)
        for term in search_terms:
            term_mask = as_text.apply(
                lambda column: column.str.contains(
                    term, case=False, na=False, regex=False
                )
            ).any(axis=1)
            mask &= term_mask
        results_df = df[mask]
        if len(results_df) > limit:
            results_df = results_df.sample(n=limit)
        results_df = results_df.sort_values(by=id_column, ascending=True)
    else:
        results_df = df.sort_values(by=id_column, ascending=True).head(limit)

    return _serialize_rows(results_df.head(limit), category)


def get_similarity_dummy(
    category: str,
    selected_columns: list,
    selected_item_id: str | None = None,
    row_normalized: bool = False,
):
    _validate_category(category)
    if category != "Student":
        raise ValueError("dummy similarity is only available for Student")

    df = load_dataframe(category)
    available_columns = set(df.columns.tolist())
    valid_col_specs = []
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
        valid_col_specs.append({"name": name, "weight": safe_weight})

    return _get_dummy_results(df, valid_col_specs, selected_item_id, category)


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
