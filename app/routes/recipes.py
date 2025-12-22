# app/routes/recipes.py
from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import Blueprint, jsonify, request, g
from sqlalchemy import func
import uuid

from ..extensions import db
from ..models.recipe import (
    Recipe,
    RecipeComment,
    RecipeIngredient,
    RecipeInstruction,
    RecipeRating,
)
from ..utils.auth import encrypt_user
from .. import require_auth

bp = Blueprint("recipes", __name__)

###########
# HELPERS
###########

def _bad_request(msg: str, status: int = 400):
    return jsonify({"message": msg}), status

def _as_float_or_none(v: Any):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except Exception:
        return None
    
def _build_cloudfront_url(key: str) -> str:
    """
    Build the public CloudFront URL for a given S3 key.
    """
    base = os.environ.get("CLOUDFRONT_IMG_BASE_URL")
    return f"{base}/{key.lstrip('/')}"

def _upload_to_s3(file_storage, key: str) -> str:
    """
    Uploads to S3 and returns the public URL matching your Next.js URL format.
    Requires AWS creds available via env/instance role.
    """
    bucket = os.environ.get("S3_BUCKET_NAME", "sophs-menu-imgs")
    region = os.environ.get("AWS_REGION")

    s3 = boto3.client("s3", region_name=region)

    # Optional: set content type
    extra_args = {}
    if getattr(file_storage, "mimetype", None):
        extra_args["ContentType"] = file_storage.mimetype

    try:
        s3.upload_fileobj(file_storage.stream, bucket, key, ExtraArgs=extra_args)
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(f"S3 upload failed: {e}")

    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

###########################
###########################
# GET ENDPOINTS
###########################
###########################

###########################
# GET ALL RECIPES
###########################
@bp.get("/")
def get_all_recipes():
    try:
        recipes = Recipe.query.with_entities(
            Recipe.recipe_id,
            Recipe.recipe_name,
            Recipe.prep_time_in_min,
            Recipe.meal,
            Recipe.rec_img_url,
            Recipe.soph_submitted,
        ).all()

        rows = []
        for r in recipes:
            rows.append({
                "recipe_id": r.recipe_id,
                "recipe_name": r.recipe_name,
                "prep_time_in_min": r.prep_time_in_min,
                "meal": r.meal,
                "rec_img_url": r.rec_img_url,
                "soph_submitted": r.soph_submitted,
            })

        return jsonify({"body": {"rows": rows}}), 200
    except Exception as e:
        return jsonify({"message": f"There was an error and we could not complete your get all recipes request. Error: {e}"}), 500

######################
# GET SINGLE RECIPE
######################
@bp.get("/<int:recipe_id>")
def get_recipe(recipe_id: int):
    if recipe_id <= 0:
        return _bad_request("Invalid recipe ID")

    try:
        recipe = Recipe.query.filter_by(recipe_id=recipe_id).first()
        if not recipe:
            return jsonify({"body": []}), 200

        instructions = (
            db.session.query(RecipeInstruction.instruction)
            .filter(RecipeInstruction.recipe_id == recipe_id)
            .order_by(RecipeInstruction.instruction_order.asc())
            .all()
        )
        instruction_list = [row.instruction for row in instructions]

        ingredients = (
            db.session.query(RecipeIngredient.ingredient)
            .filter(RecipeIngredient.recipe_id == recipe_id)
            .all()
        )
        ingredient_list = [row.ingredient for row in ingredients]

        comments = (
            db.session.query(RecipeComment.comment)
            .filter(RecipeComment.recipe_id == recipe_id)
            .all()
        )
        comment_list = [row.comment for row in comments]

        avg_rating = (
            db.session.query(func.avg(RecipeRating.rating).cast(db.Numeric(3, 1)))
            .filter(RecipeRating.recipe_id == recipe_id)
            .scalar()
        )
        average_rating = _as_float_or_none(avg_rating)

        combined = {
            "recipe_id": recipe.recipe_id,
            "recipe_name": recipe.recipe_name,
            "user_encrypted": recipe.user_encrypted,
            "prep_time_in_min": recipe.prep_time_in_min,
            "meal": recipe.meal,
            "rec_img_url": recipe.rec_img_url,
            "soph_submitted": recipe.soph_submitted,
            "ingredients": ingredient_list,
            "instructions": instruction_list,
            "comments": comment_list,
            "averageRating": average_rating,
        }

        return jsonify({"body": [combined]}), 200

    except Exception as e:
        return jsonify({"message": f"There was an error while fetching the recipe and we could not complete your request. Error: {e}"}), 500


#############################
#############################
# PROFILE SPECIFIC ENDPOINTS
#############################
#############################

###############################
# GET ALL PROFILE RECIPES
###############################

@bp.get("/profile-recipes")
@require_auth(None)
def get_profile_recipes():
    
    # Get user information from token
    token = g.authlib_server_oauth2_token
    user_sub = token.sub
    user_encrypted = encrypt_user(user_sub)
    
    try:
        rows = (
            db.session.query(
                Recipe.recipe_name,
                Recipe.recipe_id,
                Recipe.user_encrypted,
                func.coalesce(
                    func.round(func.avg(RecipeRating.rating), 1),
                    0
                ).label("avg_rating")
            )
            .outerjoin(
                RecipeRating,
                Recipe.recipe_id == RecipeRating.recipe_id
            )
            .filter(Recipe.user_encrypted == user_encrypted)
            .group_by(
                Recipe.recipe_id,
                Recipe.recipe_name,
                Recipe.user_encrypted
            )
            .order_by(Recipe.recipe_name.asc())
            .all()
        )

        result = []
        for r in rows:
            result.append({
                "recipe_name": r.recipe_name,
                "recipe_id": r.recipe_id,
                "user_encrypted": r.user_encrypted,
                "avg_rating": float(r.avg_rating) if isinstance(r.avg_rating, Decimal) else r.avg_rating,
            })

        return jsonify({"body": result}), 200

    except Exception as e:
        return jsonify({
            "message": "There was an error while fetching the recipe and we could not complete your request. Error: " + str(e)
        }), 500

###################################
# GET RATED RECIPES BY YOUR PROFILE
###################################

@bp.get("/rated-recipes")
@require_auth(None)
def get_rated_recipes():

    # Get user information from token
    token = g.authlib_server_oauth2_token
    user_sub = token.sub
    user_encrypted = encrypt_user(user_sub)

    try:
        rows = (
            db.session.query(
                Recipe.recipe_name,
                Recipe.recipe_id,
                RecipeRating.rating,
            )
            .join(RecipeRating, Recipe.recipe_id == RecipeRating.recipe_id)
            .filter(RecipeRating.user_encrypted == user_encrypted)
            .order_by(Recipe.recipe_name.asc())
            .all()
        )

        result = [
            {
                "recipe_name": r.recipe_name,
                "recipe_id": r.recipe_id,
                "rating": int(r.rating),
            }
            for r in rows
        ]

        return jsonify({"body": result}), 200

    except Exception as e:
        return jsonify({
            "message": "There was an error while fetching the rated recipes and we could not complete your request. Error: " + str(e)
        }), 500


####################################################
# PUT RECIPE DATA (IMG UPLOAD DONE THROUGH CLIENT)
####################################################

@bp.route("/", methods=["PUT", "OPTIONS"])
@require_auth(None)
def create_recipe():
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        return "", 200
    
    # Get user information from token
    token = g.authlib_server_oauth2_token
    user_sub = token.sub
    user_encrypted = encrypt_user(user_sub)

    # Parse JSON request body
    try:
        payload = request.get_json(silent=True)
        if not payload:
            return _bad_request("Request body is required")

        recipe_name = payload.get("recipe_name")
        ingredients = payload.get("ingredients")
        prep_time = payload.get("prep_time")
        meal = payload.get("meal")
        instructions = payload.get("instructions")
        img_public_url = payload.get("img_public_url") 
        soph_submitted = payload.get("soph_submitted", False)

        ####################
        # Validating Inputs
        ####################
        
        # Check required fields exist
        if not recipe_name or not ingredients or not instructions or not meal:
            return _bad_request("Missing required fields")
        
        # Validate recipe name
        if not isinstance(recipe_name, str) or not recipe_name.strip():
            return _bad_request("Recipe name must be a non-empty string")
        
        # Validate meal
        if not isinstance(meal, str) or not meal.strip():
            return _bad_request("Meal must be a non-empty string")
        
        # Validate ingredients
        if not isinstance(ingredients, list):
            return _bad_request("Ingredients must be an array")
        if len(ingredients) == 0:
            return _bad_request("At least one ingredient is required")
        for idx, ingredient in enumerate(ingredients):
            if not isinstance(ingredient, str) or not ingredient.strip():
                return _bad_request(f"Ingredient at index {idx} must be a non-empty string")
        
        # Validate instructions
        if not isinstance(instructions, list):
            return _bad_request("Instructions must be an array")
        if len(instructions) == 0:
            return _bad_request("At least one instruction is required")
        for idx, instruction in enumerate(instructions):
            if not isinstance(instruction, str) or not instruction.strip():
                return _bad_request(f"Instruction at index {idx} must be a non-empty string")
        
        # Validate prep time
        if prep_time is None:
            return _bad_request("Prep time is required")
        try:
            prep_time_int = int(prep_time)
        except (ValueError, TypeError):
            return _bad_request("Prep time must be a valid number")
        if prep_time_int < 0:
            return _bad_request("Prep time cannot be negative")
        
        # Validate image URL
        if not img_public_url or not isinstance(img_public_url, str):
            return _bad_request("Image URL is required")
        img_public_url_stripped = img_public_url.strip()
        if not img_public_url_stripped:
            return _bad_request("Image URL cannot be empty")
        
        # Optional: Validate URL is from expected CloudFront domain
        cloudfront_base = os.environ.get("CLOUDFRONT_IMG_BASE_URL", "")
        if cloudfront_base and not img_public_url_stripped.startswith(cloudfront_base):
            return _bad_request("Image URL must be from the expected domain")
        
        # Validate soph_submitted is boolean
        if not isinstance(soph_submitted, bool):
            return _bad_request("soph_submitted must be a boolean")
        
        # Sanitize inputs
        sanitized_recipe_name = recipe_name.strip()[:255]
        sanitized_meal = meal.strip()[:50]
        sanitized_img_public_url = img_public_url_stripped[:500]  # Add max length for URLs

    except Exception as e:
        return jsonify({"message": f"Failed to parse request: {e}"}), 400

    ##################
    # TRY INFO UPLOAD
    ##################
    try:
        with db.session.begin():
            recipe = Recipe(
                recipe_name=sanitized_recipe_name,
                prep_time_in_min=prep_time_int,
                meal=sanitized_meal,
                user_encrypted=user_encrypted,
                soph_submitted=soph_submitted,
                rec_img_url=sanitized_img_public_url,
            )
            db.session.add(recipe)
            db.session.flush()  # get recipe.recipe_id without committing

            recipe_id = recipe.recipe_id

            # Instructions
            for i, instruction in enumerate(instructions):
                sanitized_instruction = str(instruction).strip()[:1000]
                db.session.add(RecipeInstruction(
                    recipe_id=recipe_id,
                    instruction_order=i,
                    instruction=sanitized_instruction,
                ))

            # Ingredients
            for ingredient in ingredients:
                sanitized_ingredient = str(ingredient).strip()[:255]
                db.session.add(RecipeIngredient(
                    recipe_id=recipe_id,
                    ingredient=sanitized_ingredient,
                ))

        return jsonify({"message": "Recipe created successfully", "recipe_id": recipe_id}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Failed to create recipe: {e}"}), 500

###############################
# PUT [ID]: ADD COMMENT TO ID
###############################

@bp.route("/<int:recipe_id>", methods=["PUT", "OPTIONS"])
@require_auth(None)
def add_comment(recipe_id: int):
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        return "", 200

    if recipe_id <= 0:
        return _bad_request("Invalid recipe ID")

    # Get user information from token
    token = g.authlib_server_oauth2_token
    user_sub = token.sub
    user_encrypted = encrypt_user(user_sub)

    try:
        body = request.get_json(silent=True) or {}
        comment = body.get("comment")

        if not comment or not isinstance(comment, str) or len(comment.strip()) == 0:
            return _bad_request("Comment is required")

        sanitized_comment = comment.strip()[:150]

        # Ensure recipe exists (optional but helpful)
        exists = db.session.query(Recipe.recipe_id).filter(Recipe.recipe_id == recipe_id).first()
        if not exists:
            return jsonify({"message": "Invalid recipe ID"}), 400

        db.session.add(RecipeComment(
            recipe_id=recipe_id,
            comment=sanitized_comment,
            user_encrypted=user_encrypted,
        ))
        db.session.commit()

        return jsonify({"message": "Comment added successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"There was an error while sending the comment. Error: {e}"}), 500

##############################
##############################
# RATINGS
##############################
##############################

##############################
# PUT [ID]: VOTE ON RATING
##############################

@bp.route("/<int:recipe_id>/rating", methods=["PUT", "OPTIONS"])
@require_auth(None)
def submit_rating(recipe_id: int):
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        return "", 200
    
    if recipe_id <= 0:
        return _bad_request("Invalid recipe ID")

    # Get user information from token
    token = g.authlib_server_oauth2_token
    user_sub = token.sub
    user_encrypted = encrypt_user(user_sub)

    body = request.get_json(silent=True) or {}
    rating = body.get("rating")

    # Validate rating
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return _bad_request("Rating must be a number between 1 and 5")

    try:
        existing = RecipeRating.query.filter_by(recipe_id=recipe_id, user_encrypted=user_encrypted).first()
        if existing:
            existing.rating = rating
        else:
            db.session.add(RecipeRating(recipe_id=recipe_id, user_encrypted=user_encrypted, rating=rating))

        db.session.commit()
        return jsonify({"message": "Rating submitted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"There was an error while submitting the rating. Error: {e}"}), 500

#########################################
# GET [ID]: GET USERS RATING OF RECIPE
#########################################

@bp.get("/<int:recipe_id>/rating")
@require_auth(None)
def get_users_rating(recipe_id: int):
    
    if recipe_id <= 0:
        return _bad_request("Invalid recipe ID")

    # Get user information from token
    token = g.authlib_server_oauth2_token
    user_sub = token.sub
    user_encrypted = encrypt_user(user_sub)

    try:
        row = RecipeRating.query.with_entities(RecipeRating.rating).filter_by(
            recipe_id=recipe_id,
            user_encrypted=user_encrypted,
        ).first()

        if not row:
            return jsonify({"usersRating": 0}), 200

        rating_value = int(row.rating)
        return jsonify({"usersRating": rating_value}), 200

    except Exception as e:
        return jsonify({"message": f"There was an error while fetching users rating. Error: {e}"}), 500
    

###############################
# POST: PRESIGN IMAGE UPLOAD
# This doesn't upload anything, it just generates the information that we can send to the client
# with the information that this api sends back the client can upload the image
###############################
@bp.route("/presign-image-upload", methods=["POST", "OPTIONS"])
@require_auth(None)
def presign_recipe_image_upload():
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        return "", 200

    # Get user information from token
    token = g.authlib_server_oauth2_token
    user_sub = token.sub
    user_encrypted = encrypt_user(user_sub)

    body = request.get_json(silent=True) or {}
    content_type = body.get("contentType")

    # Validate content type
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if not content_type or content_type not in allowed:
        return _bad_request(f"Invalid or missing contentType. Allowed: {sorted(list(allowed))}")

    bucket = os.environ.get("S3_BUCKET_NAME")
    region = os.environ.get("AWS_REGION")
    prefix = os.environ.get("S3_UPLOAD_PREFIX")

    # Choose extension based on content type
    ext_map = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }
    ext = ext_map[content_type]

    # Key like: imgs/<user_encrypted>/<uuid>.jpg
    key = f"{prefix}/{user_encrypted}/{uuid.uuid4().hex}.{ext}"

    s3 = boto3.client("s3", region_name=region)

    try:
        upload_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=500,
        )
    except (BotoCoreError, ClientError) as e:
        return jsonify({"message": f"Failed to generate presigned URL: {e}"}), 500

    img_public_url = _build_cloudfront_url(key)

    return jsonify({
        "uploadUrl": upload_url,
        "key": key,
        "publicUrl": img_public_url,
    }), 200
