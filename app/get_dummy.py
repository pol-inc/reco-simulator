from pathlib import Path

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
                "id": str(data.get(id_column, "")),
                "primaryText": str(data.get(title_column, "")),
                "secondaryText": str(data.get(id_column, "")),
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
    return df.columns.tolist()


def search_items(category: str, keyword: str, limit: int = 20):
    df = load_dataframe(category)
    keyword = (keyword or "").strip()

    if keyword:
        mask = (
            df.astype(str)
            .apply(
                lambda column: column.str.contains(keyword, case=False, na=False, regex=False)
            )
            .any(axis=1)
        )
        results_df = df[mask]
    else:
        results_df = df

    return _serialize_rows(results_df.head(limit), category)


def get_similarity_dummy(
    category: str,
    selected_columns: list[str],
    method: str,
    selected_item_id: str | None = None,
):
    _validate_category(category)
    if method not in {"Sum", "Min"}:
        raise ValueError("method must be Sum or Min")

    df = load_dataframe(category)
    valid_columns = [col for col in selected_columns if col in df.columns]
    config = CATEGORY_CONFIG[category]
    id_column = config["id_column"]
    title_column = config["title_column"]
    base_offset = sum(ord(ch) for ch in str(selected_item_id or "")) % 7

    # Requirement says to always show CSV rows 11-20 as the top similarity items.
    candidates = df.iloc[10:20]
    items = []

    for rank, (_, row) in enumerate(candidates.iterrows(), start=1):
        row_data = {col: _to_native(row[col]) for col in df.columns}
        selected_values = {col: row_data[col] for col in valid_columns}
        if method == "Sum":
            score = round(max(0.0, 96.0 - rank * 3.1 - len(valid_columns) - base_offset), 2)
        else:
            score = round(max(0.0, 91.0 - rank * 2.4 - len(valid_columns) * 0.8 - base_offset), 2)

        items.append(
            {
                "id": str(row_data.get(id_column, "")),
                "primaryText": str(row_data.get(title_column, "")),
                "secondaryText": str(row_data.get(id_column, "")),
                "selectedValues": selected_values,
                "score": score,
                "method": method,
                "data": row_data,
            }
        )

    return items
