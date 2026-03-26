from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RECRUIT_CSV_PATH = BASE_DIR / "data" / "recruit_info.csv"
RECRUIT_ID_MAP_PATH = BASE_DIR / "data" / "scores_Recruit_id_map.npy"
RECRUIT_PARTIAL_MATCH_COLUMNS = {
	"recruit_name",
	"company_name",
	"research_fields",
	"research_classifications",
	"occupation",
	"recruit_type_name",
	"work_locations",
}

_topk_cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}
_id_map_cache: list[str] | None = None


def get_recruit_column_definitions(available_columns: list[str]) -> list[dict[str, object]]:
	definitions = []
	for column in available_columns:
		is_partial_match = column in RECRUIT_PARTIAL_MATCH_COLUMNS
		definitions.append(
			{
				"name": column,
				"label": f"{column}（部分一致）" if is_partial_match else column,
				"min": 0,
				"max": 1 if is_partial_match else 10,
				"step": 0.1,
				"defaultWeight": 0.1 if is_partial_match else 1,
				"matchType": "partial" if is_partial_match else "score",
			}
		)
	return definitions


def _load_recruit_dataframe() -> pd.DataFrame:
	return pd.read_csv(RECRUIT_CSV_PATH)


def _to_native(value):
	if pd.isna(value):
		return ""
	if hasattr(value, "item"):
		try:
			return value.item()
		except ValueError:
			return value
	return value


def _load_top_k(col_name: str) -> tuple[np.ndarray, np.ndarray]:
	if col_name not in _topk_cache:
		data_dir = BASE_DIR / "data"
		indices = np.load(str(data_dir / f"scores_{col_name}_indices.npy"))
		scores_arr = np.load(str(data_dir / f"scores_{col_name}_scores.npy"))
		_topk_cache[col_name] = (indices, scores_arr)
	return _topk_cache[col_name]


def _load_id_map() -> list[str]:
	global _id_map_cache
	if _id_map_cache is None:
		if not RECRUIT_ID_MAP_PATH.exists():
			raise FileNotFoundError("scores_Recruit_id_map.npy was not found")
		id_map = np.load(str(RECRUIT_ID_MAP_PATH), allow_pickle=True)
		_id_map_cache = [str(value) for value in id_map]
	return _id_map_cache


def _normalize_column_specs(selected_columns: list, available_columns: list[str]):
	valid_columns = set(available_columns)
	col_specs = []

	for item in selected_columns:
		if isinstance(item, dict):
			name = str(item.get("name", ""))
			weight = float(item.get("weight", 1.0))
		else:
			name = str(item)
			weight = 1.0

		if name not in valid_columns:
			continue

		max_weight = 1.0 if name in RECRUIT_PARTIAL_MATCH_COLUMNS else 10.0
		safe_weight = min(max_weight, max(0.0, weight))
		if safe_weight <= 0.0:
			continue

		col_specs.append({"name": name, "weight": safe_weight})

	return col_specs


def _split_categories(value) -> set[str]:
	text = str(_to_native(value)).strip()
	if not text:
		return set()
	return {part.strip() for part in text.split(",") if part.strip()}


def _apply_vector_scores(
	agg_scores: dict[int, dict[str, float]],
	query_idx: int,
	col_name: str,
	weight: float,
	row_normalized: bool,
):
	indices_arr, scores_arr = _load_top_k(col_name)
	row_indices = indices_arr[query_idx]
	row_scores = scores_arr[query_idx].astype(np.float64)

	if row_normalized:
		row_sum = row_scores.sum()
		if row_sum > 0:
			row_scores = row_scores / row_sum

	for ridx, score in zip(row_indices, row_scores):
		ridx = int(ridx)
		if ridx < 0:
			continue
		agg_scores.setdefault(ridx, {})[col_name] = float(score) * weight


def _apply_partial_match_scores(
	agg_scores: dict[int, dict[str, float]],
	df: pd.DataFrame,
	query_idx: int,
	col_name: str,
	weight: float,
):
	query_values = _split_categories(df.iloc[query_idx][col_name])
	if not query_values:
		return

	for ridx, value in enumerate(df[col_name].tolist()):
		if ridx == query_idx:
			continue
		if query_values.intersection(_split_categories(value)):
			agg_scores.setdefault(ridx, {})[col_name] = weight


def get_recruit_similarity(
	selected_columns: list,
	selected_item_id: str | None = None,
	row_normalized: bool = False,
):
	df = _load_recruit_dataframe()
	valid_col_specs = _normalize_column_specs(selected_columns, df.columns.tolist())
	if not valid_col_specs:
		return []

	query_str = str(selected_item_id) if selected_item_id is not None else ""
	id_map = _load_id_map()
	if query_str not in id_map:
		return []

	query_idx = id_map.index(query_str)
	agg_scores: dict[int, dict[str, float]] = {}

	for col_spec in valid_col_specs:
		col_name = col_spec["name"]
		weight = col_spec["weight"]

		if col_name in RECRUIT_PARTIAL_MATCH_COLUMNS:
			_apply_partial_match_scores(agg_scores, df, query_idx, col_name, weight)
			continue

		_apply_vector_scores(
			agg_scores,
			query_idx,
			col_name,
			weight,
			row_normalized,
		)

	final_scores: list[tuple[int, float]] = []
	for ridx, col_scores in agg_scores.items():
		if ridx == query_idx:
			continue
		final_scores.append((ridx, sum(col_scores.values())))

	final_scores.sort(key=lambda item: item[1], reverse=True)

	results = []
	for ridx, score in final_scores[:20]:
		row = df.iloc[ridx]
		row_data = {col: _to_native(row[col]) for col in df.columns}
		selected_values = {
			col_spec["name"]: row_data.get(col_spec["name"], "")
			for col_spec in valid_col_specs
		}
		results.append(
			{
				"id": str(row_data.get("recruit_id", "")),
				"primaryText": str(row_data.get("recruit_name", "")),
				"secondaryText": str(row_data.get("recruit_id", "")),
				"selectedValues": selected_values,
				"score": round(score, 4),
				"method": "WeightedSum",
				"data": row_data,
			}
		)

	return results
