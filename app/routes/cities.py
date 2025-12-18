# app/routes/cities.py
from flask import Blueprint, request, jsonify
from ..models.city import City

bp = Blueprint("cities", __name__)

@bp.get("/")
def get_cities_by_state():
    """
    GET /api/cities?state=CA
    """
    state = request.args.get("state")

    if not state:
        return jsonify(error="`state` query parameter is required"), 400

    cities = (
        City.query
        .filter(City.state_code == state.upper())
        .order_by(City.city.asc())
        .all()
    )

    return jsonify({
        "body": [c.to_dict() for c in cities]
    }), 200
