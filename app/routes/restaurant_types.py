from flask import Blueprint, jsonify, g
from ..models.restaurant_type import RestaurantType
from .. import require_auth

from ..utils.auth import require_user, encrypt_user

bp = Blueprint("restaurant_types", __name__)

@bp.get("/")
@require_auth(None)
def get_restaurant_types():
    try:
        ####
        # TEMP

        print("Getting token")
        token = g.authlib_server_oauth2_token
        print("this is token")
        print(token)

        print("getting user_sub from token")
        user_sub = token.sub
        print("this is token")
        print(token)

        user_encrypted = encrypt_user(user_sub)
        print("this is user encrypted")
        print(user_encrypted)

        return jsonify({"body": user_sub}), 200


        # END TEMP
        ######



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