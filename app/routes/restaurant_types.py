from flask import Blueprint, jsonify
from ..models.restaurant_type import RestaurantType
from .. import require_auth

bp = Blueprint("restaurant_types", __name__)

@bp.get("/")
@require_auth(None)
def get_restaurant_types():
    try:
        rows = (
            RestaurantType.query
            .with_entities(RestaurantType.rest_type)
            .order_by(RestaurantType.rest_type.asc())
            .all()
        )
        restaurant_types = [r.rest_type for r in rows]
        return jsonify({"body": restaurant_types}), 200

    except Exception as e:
        return jsonify({
            "message": "There was an error while fetching restaurant types and we could not complete your request. Error: " + str(e)
        }), 500