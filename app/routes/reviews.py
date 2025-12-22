from __future__ import annotations
from flask import Blueprint, jsonify, request, g
from sqlalchemy import desc
from decimal import Decimal
from ..extensions import db
from ..models.review import Review, RestTypeReviewRef
from ..models.restaurant_type import RestaurantType
from ..utils.auth import encrypt_user
from .. import require_auth

bp = Blueprint("reviews", __name__)

def _bad_request(msg: str, status: int = 400):
    return jsonify({"message": msg}), status

def _num(v):
    # normalize Decimal -> float for JSON
    if isinstance(v, Decimal):
        return float(v)
    return v

###############################
# GET ALL REVIEWS
###############################
@bp.get("/")
def get_all_reviews():
    try:
        rows = (
            db.session.query(
                Review,
                RestaurantType.rest_type,
            )
            .outerjoin(RestTypeReviewRef, Review.review_id == RestTypeReviewRef.review_id)
            .outerjoin(RestaurantType, RestTypeReviewRef.rest_type_id == RestaurantType.rest_type_id)
            .order_by(desc(Review.review_id))
            .all()
        )

        out_rows = []
        for review, rest_type in rows:
            out_rows.append({
                "review_id": review.review_id,
                "rest_name": review.rest_name,
                "o_rating": _num(review.o_rating),
                "price": review.price,
                "taste": _num(review.taste),
                "experience": _num(review.experience),
                "description": review.description,
                "city": review.city,
                "state_code": review.state_code,
                "soph_submitted": review.soph_submitted,
                "user_encrypted": review.user_encrypted,
                "rest_type": rest_type,  # may be None if no ref row
            })

        return jsonify({"body": {"rows": out_rows}}), 200

    except Exception as e:
        return jsonify({
            "message": "There was an error and we could not complete your get all reviews request. Error: " + str(e)
        }), 500


###############################
# PUT REVIEW (CREATE)
###############################
@bp.route("/", methods=["PUT", "OPTIONS"])
@require_auth(None)
def create_review():
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        return "", 200

    # Get user information from token
    token = g.authlib_server_oauth2_token
    user_sub = token.sub
    user_encrypted = encrypt_user(user_sub)

    try:
        body = request.get_json(silent=True) or {}

        rest_name = body.get("rest_name")
        rest_type = body.get("rest_type")
        o_rating = body.get("o_rating")
        price = body.get("price")
        taste = body.get("taste")
        experience = body.get("experience")
        description = body.get("description")
        city = body.get("city")
        state_code = body.get("state_code")

        # Required fields
        if not rest_name or not rest_type or not city or not state_code:
            return _bad_request("Missing required fields")

        # Validate numeric fields
        try:
            o_rating_f = float(o_rating)
            taste_f = float(taste)
            exp_f = float(experience)
        except Exception:
            return _bad_request("overall rating, taste, and experience fields must be numbers between 1-10")

        if any(v <= 0 or v > 10 for v in [o_rating_f, taste_f, exp_f]):
            return _bad_request("overall rating, taste, and experience fields must be numbers between 1-10")

        try:
            price_i = int(price)
        except Exception:
            return _bad_request("price field must be a number between 1-4")

        if price_i <= 0 or price_i > 4:
            return _bad_request("price field must be a number between 1-4")

        # Sanitize strings
        sanitized_rest_name = str(rest_name).strip()[:255]
        sanitized_description = (str(description).strip()[:1000]) if description else ""
        sanitized_city = str(city).strip()[:100]
        sanitized_state_code = str(state_code).strip()[:2]
        sanitized_rest_type = str(rest_type).strip()

        # Transaction: insert review + lookup rest_type_id + insert junction row
        with db.session.begin():
            review = Review(
                rest_name=sanitized_rest_name,
                o_rating=o_rating_f,
                price=price_i,
                taste=taste_f,
                experience=exp_f,
                description=sanitized_description,
                city=sanitized_city,
                state_code=sanitized_state_code,
                soph_submitted=False,
                user_encrypted=user_encrypted,
            )
            db.session.add(review)
            db.session.flush()  # gets review.review_id

            # lookup restaurant type id
            rt = (
                db.session.query(RestaurantType)
                .filter(RestaurantType.rest_type == sanitized_rest_type)
                .first()
            )
            if not rt:
                # Raising causes rollback via session.begin()
                raise ValueError("Invalid restaurant type")

            db.session.add(RestTypeReviewRef(
                rest_type_id=rt.rest_type_id,
                review_id=review.review_id,
            ))

        return jsonify({"message": "Review created successfully"}), 200

    except ValueError as e:
        # Invalid restaurant type or other controlled validation failure
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to create review"}), 500


###############################
# GET REVIEW BY ID
###############################
@bp.get("/<int:review_id>")
def get_review(review_id: int):
    if review_id <= 0:
        return _bad_request("Invalid review ID")

    try:
        rows = (
            db.session.query(
                Review,
                RestaurantType.rest_type,
            )
            .outerjoin(RestTypeReviewRef, Review.review_id == RestTypeReviewRef.review_id)
            .outerjoin(RestaurantType, RestTypeReviewRef.rest_type_id == RestaurantType.rest_type_id)
            .filter(Review.review_id == review_id)
            .all()
        )

        out = []
        for review, rest_type in rows:
            out.append({
                "review_id": review.review_id,
                "rest_name": review.rest_name,
                "o_rating": _num(review.o_rating),
                "price": review.price,
                "taste": _num(review.taste),
                "experience": _num(review.experience),
                "description": review.description,
                "city": review.city,
                "state_code": review.state_code,
                "soph_submitted": review.soph_submitted,
                "user_encrypted": review.user_encrypted,
                "rest_type": rest_type,
            })

        return jsonify({"body": out}), 200

    except Exception as e:
        return jsonify({
            "message": "There was an error while fetching the review and we could not complete your request. Error: " + str(e)
        }), 500


###############################
# GET PROFILE REVIEWS
###############################
@bp.route("/profile-reviews")
@require_auth(None)
def get_profile_reviews():  

    # Get user information from token
    token = g.authlib_server_oauth2_token
    user_sub = token.sub
    user_encrypted = encrypt_user(user_sub)

    try:
        rows = (
            db.session.query(
                Review.rest_name,
                Review.o_rating,
                Review.user_encrypted,
                Review.review_id,
            )
            .filter(Review.user_encrypted == user_encrypted)
            .all()
        )

        out = [{
            "rest_name": r.rest_name,
            "o_rating": _num(r.o_rating),
            "user_encrypted": r.user_encrypted,
            "review_id": r.review_id,
        } for r in rows]

        return jsonify({"body": out}), 200

    except Exception as e:
        return jsonify({
            "message": "There was an error while fetching the review and we could not complete your request. Error: " + str(e)
        }), 500