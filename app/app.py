from flask import Flask, jsonify, render_template, request

from app.get_dummy import get_columns, get_similarity_dummy, search_items

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/columns")
def columns():
    category = request.args.get("category", "")
    try:
        columns_data = get_columns(category)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"category": category, "columns": columns_data})


@app.route("/api/search")
def search():
    category = request.args.get("category", "")
    keyword = request.args.get("q", "")
    limit_text = request.args.get("limit", "20")

    try:
        limit = max(1, min(100, int(limit_text)))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    try:
        items = search_items(category, keyword, limit=limit)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "category": category,
            "keyword": keyword,
            "count": len(items),
            "items": items,
        }
    )


@app.route("/api/similarity", methods=["POST"])
def similarity():
    payload = request.get_json(silent=True) or {}
    category = payload.get("category", "")
    method = payload.get("method", "Sum")
    selected_columns = payload.get("columns", [])
    selected_item_id = payload.get("selectedItemId")

    if not isinstance(selected_columns, list):
        return jsonify({"error": "columns must be an array"}), 400

    try:
        items = get_similarity_dummy(
            category=category,
            selected_columns=selected_columns,
            method=method,
            selected_item_id=selected_item_id,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "category": category,
            "method": method,
            "count": len(items),
            "items": items,
        }
    )
