from __future__ import annotations
import os

from flask import Blueprint, jsonify, request
from sqlalchemy import desc
from decimal import Decimal

from ..extensions import db
from ..models.review import Review, RestTypeReviewRef
from ..models.restaurant_type import RestaurantType

bp = Blueprint("reviews", __name__)

from ..utils.auth import require_user, encrypt_email

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
@bp.route("/<string:user_email>", methods=["PUT", "OPTIONS"])
def create_review(user_email: str):
    print("\n" + "="*60)
    print("CREATE_REVIEW: Function called")
    print(f"CREATE_REVIEW: Request method: {request.method}")
    print(f"CREATE_REVIEW: User email parameter: {user_email}")
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        print("CREATE_REVIEW: OPTIONS request - returning 200")
        return jsonify({}), 200
    
    try:
        print(f"CREATE_REVIEW: Attempting to encrypt email: {user_email}")
        user_encrypted = encrypt_email(user_email)
        print(f"CREATE_REVIEW: Email encrypted successfully: {user_encrypted}")
        ##FIX THISSS
        #I should configure the frontend to send the users email in the request then use the require user function to get the email then encrypt it.
        #user_encrypted = require_user()
    except PermissionError as pe:
        print(f"CREATE_REVIEW: PermissionError during email encryption: {pe}")
        return jsonify({"message": "Unauthorized"}), 401
    except Exception as e:
        print(f"CREATE_REVIEW: Unexpected error during email encryption: {e}")
        return jsonify({"message": "Unauthorized"}), 401

    try:
        print("CREATE_REVIEW: Parsing request body")
        body = request.get_json(silent=True) or {}
        print(f"CREATE_REVIEW: Raw body received: {body}")

        rest_name = body.get("rest_name")
        rest_type = body.get("rest_type")
        o_rating = body.get("o_rating")
        price = body.get("price")
        taste = body.get("taste")
        experience = body.get("experience")
        description = body.get("description")
        city = body.get("city")
        state_code = body.get("state_code")

        print(f"CREATE_REVIEW: Extracted fields:")
        print(f"  - rest_name: {rest_name} (type: {type(rest_name)})")
        print(f"  - rest_type: {rest_type} (type: {type(rest_type)})")
        print(f"  - o_rating: {o_rating} (type: {type(o_rating)})")
        print(f"  - price: {price} (type: {type(price)})")
        print(f"  - taste: {taste} (type: {type(taste)})")
        print(f"  - experience: {experience} (type: {type(experience)})")
        print(f"  - description: {description} (type: {type(description)})")
        print(f"  - city: {city} (type: {type(city)})")
        print(f"  - state_code: {state_code} (type: {type(state_code)})")

        # Required fields
        print("CREATE_REVIEW: Validating required fields")
        if not rest_name or not rest_type or not city or not state_code:
            print(f"CREATE_REVIEW: Missing required fields - rest_name={bool(rest_name)}, rest_type={bool(rest_type)}, city={bool(city)}, state_code={bool(state_code)}")
            return _bad_request("Missing required fields")
        print("CREATE_REVIEW: All required fields present")

        # Validate numeric fields
        print("CREATE_REVIEW: Validating numeric fields (o_rating, taste, experience)")
        try:
            o_rating_f = float(o_rating)
            taste_f = float(taste)
            exp_f = float(experience)
            print(f"CREATE_REVIEW: Numeric conversion successful - o_rating={o_rating_f}, taste={taste_f}, experience={exp_f}")
        except Exception as e:
            print(f"CREATE_REVIEW: Failed to convert ratings to float: {e}")
            return _bad_request("overall rating, taste, and experience fields must be numbers between 1-10")

        if any(v <= 0 or v > 10 for v in [o_rating_f, taste_f, exp_f]):
            print(f"CREATE_REVIEW: Rating values out of range: o_rating={o_rating_f}, taste={taste_f}, experience={exp_f}")
            return _bad_request("overall rating, taste, and experience fields must be numbers between 1-10")
        print("CREATE_REVIEW: Rating values within valid range (1-10)")

        print("CREATE_REVIEW: Validating price field")
        try:
            price_i = int(price)
            print(f"CREATE_REVIEW: Price converted to int: {price_i}")
        except Exception as e:
            print(f"CREATE_REVIEW: Failed to convert price to int: {e}")
            return _bad_request("price field must be a number between 1-4")

        if price_i <= 0 or price_i > 4:
            print(f"CREATE_REVIEW: Price out of range: {price_i}")
            return _bad_request("price field must be a number between 1-4")
        print("CREATE_REVIEW: Price within valid range (1-4)")

        # Sanitize strings
        print("CREATE_REVIEW: Sanitizing string fields")
        sanitized_rest_name = str(rest_name).strip()[:255]
        sanitized_description = (str(description).strip()[:1000]) if description else ""
        sanitized_city = str(city).strip()[:100]
        sanitized_state_code = str(state_code).strip()[:2]
        sanitized_rest_type = str(rest_type).strip()
        
        print(f"CREATE_REVIEW: Sanitized values:")
        print(f"  - sanitized_rest_name: '{sanitized_rest_name}' (len: {len(sanitized_rest_name)})")
        print(f"  - sanitized_rest_type: '{sanitized_rest_type}' (len: {len(sanitized_rest_type)})")
        print(f"  - sanitized_city: '{sanitized_city}' (len: {len(sanitized_city)})")
        print(f"  - sanitized_state_code: '{sanitized_state_code}' (len: {len(sanitized_state_code)})")
        print(f"  - sanitized_description: '{sanitized_description[:50]}...' (len: {len(sanitized_description)})")

        # Transaction: insert review + lookup rest_type_id + insert junction row
        print("CREATE_REVIEW: Starting database transaction")
        with db.session.begin():
            print("CREATE_REVIEW: Creating Review object")
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
            print(f"CREATE_REVIEW: Review object created: {review}")
            
            db.session.add(review)
            print("CREATE_REVIEW: Review added to session")
            
            db.session.flush()  # gets review.review_id
            print(f"CREATE_REVIEW: Session flushed - review_id assigned: {review.review_id}")

            # lookup restaurant type id
            print(f"CREATE_REVIEW: Looking up restaurant type: '{sanitized_rest_type}'")
            rt = (
                db.session.query(RestaurantType)
                .filter(RestaurantType.rest_type == sanitized_rest_type)
                .first()
            )
            
            if not rt:
                print(f"CREATE_REVIEW: ERROR - Restaurant type not found: '{sanitized_rest_type}'")
                print("CREATE_REVIEW: Available restaurant types:")
                all_types = db.session.query(RestaurantType).all()
                for t in all_types:
                    print(f"  - '{t.rest_type}' (id: {t.rest_type_id})")
                # Raising causes rollback via session.begin()
                raise ValueError("Invalid restaurant type")
            
            print(f"CREATE_REVIEW: Restaurant type found - id: {rt.rest_type_id}, name: '{rt.rest_type}'")
            
            print("CREATE_REVIEW: Creating RestTypeReviewRef junction row")
            junction_row = RestTypeReviewRef(
                rest_type_id=rt.rest_type_id,
                review_id=review.review_id,
            )
            db.session.add(junction_row)
            print(f"CREATE_REVIEW: Junction row added - rest_type_id: {rt.rest_type_id}, review_id: {review.review_id}")

        print("CREATE_REVIEW: Transaction committed successfully")
        print("="*60 + "\n")
        return jsonify({"message": "Review created successfully"}), 200

    except ValueError as e:
        # Invalid restaurant type or other controlled validation failure
        print(f"CREATE_REVIEW: ValueError caught: {e}")
        print("="*60 + "\n")
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        print(f"CREATE_REVIEW: Unexpected exception caught: {type(e).__name__}: {e}")
        import traceback
        print(f"CREATE_REVIEW: Traceback:\n{traceback.format_exc()}")
        db.session.rollback()
        print("CREATE_REVIEW: Session rolled back")
        print("="*60 + "\n")
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
@bp.route("/profile-reviews/<string:user_email>", methods=["GET", "OPTIONS"])
def get_profile_reviews(user_email: str):
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return jsonify({}), 200
    
    try:
        user_encrypted = encrypt_email(user_email)
        ##FIX THISSS
        #I should configure the frontend to send the users email in the request then use the require user function to get the email then encrypt it.
        #user_encrypted = require_user()
    except PermissionError:
        return jsonify({"message": "Unauthorized"}), 401

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