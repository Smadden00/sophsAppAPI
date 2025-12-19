# app/routes/recipes.py
from __future__ import annotations

import hashlib
import json
import os
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import Blueprint, jsonify, request
from sqlalchemy import func

from ..extensions import db
from ..models.recipe import (
    Recipe,
    RecipeComment,
    RecipeIngredient,
    RecipeInstruction,
    RecipeRating,
)

bp = Blueprint("recipes", __name__)

######################
# AUTH PLACEHOLDER!!!
######################

def encrypt_email(email: str) -> str:
    # 64 hex chars to match VARCHAR(64)
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()

def require_user() -> str:
    email = request.headers.get("X-User-Email")
    if not email:
        # mirrors your 401 Unauthorized behavior
        raise PermissionError("Unauthorized")
    return encrypt_email(email)

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

        # CHANGE HERE FROM THE PREVIOUS IMPLEMENTATION
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
            "rating": _as_float_or_none(recipe.rating),
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

#######################################################################################################
# PUT RECIPE
# Expects:
#   - form field "data": JSON string with recipe_name, ingredients[], prep_time_in_min, meal, instructions[]
#   - file field (any): image file
#######################################################################################################

@bp.put("/")
def create_recipe():
    try:
        user_encrypted = require_user()
    except PermissionError:
        return jsonify({"message": "Unauthorized"}), 401

    # Parse multipart: request.form + request.files
    try:
        data_str = request.form.get("data")
        if not data_str:
            return _bad_request("Missing required form field: data")
        payload = json.loads(data_str)

        recipe_name = payload.get("recipe_name")
        ingredients = payload.get("ingredients")
        prep_time_in_min = payload.get("prep_time_in_min")
        meal = payload.get("meal")
        instructions = payload.get("instructions")

        # Input validation (mirrors your Next.js checks)
        if not recipe_name or not ingredients or not instructions or not meal:
            return _bad_request("Missing required fields")
        if not isinstance(ingredients, list) or not isinstance(instructions, list):
            return _bad_request("ingredients and instructions must be arrays")
        try:
            prep_time_in_min_int = int(prep_time_in_min)
        except Exception:
            return _bad_request("Invalid prep_time_in_min value")
        if prep_time_in_min_int < 0:
            return _bad_request("Invalid prep_time_in_min value")

        default_rating = Decimal("0.0")

        sanitized_recipe_name = str(recipe_name).strip()[:255]
        sanitized_meal = str(meal).strip()[:50]

        # Grab an uploaded file
        uploaded_file = None
        if request.files:
            # take the first file
            uploaded_file = next(iter(request.files.values()))

        if uploaded_file is None:
            return _bad_request("Missing image file upload")

    except json.JSONDecodeError:
        return _bad_request("Invalid JSON in form field: data")
    except Exception as e:
        return jsonify({"message": f"Failed to parse request: {e}"}), 400

    try:
        with db.session.begin():
            recipe = Recipe(
                recipe_name=sanitized_recipe_name,
                prep_time_in_min=prep_time_in_min_int,
                meal=sanitized_meal,
                user_encrypted=user_encrypted,
                rating=default_rating,
                soph_submitted=False,
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

            ###TO DO LATER: FIX THE UPLOAD TO S3!!!!!
            #Right now it won't work because S3 only accepts files from the frontend server

            # Upload to S3 and store URL
            image_url = _upload_to_s3(uploaded_file, key=str(recipe_id))
            recipe.rec_img_url = image_url

        return jsonify({"message": "Recipe created successfully", "recipe_id": recipe_id}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Failed to create recipe: {e}"}), 500

###############################
# PUT [ID]: ADD COMMENT TO ID
###############################

@bp.put("/<int:recipe_id>")
def add_comment(recipe_id: int):
    if recipe_id <= 0:
        return _bad_request("Invalid recipe ID")

    try:
        user_encrypted = require_user()
    except PermissionError:
        return jsonify({"message": "Unauthorized"}), 401

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
# POST [ID]: VOTE ON RATING
##############################

@bp.post("/<int:recipe_id>/rating")
def submit_rating(recipe_id: int):
    if recipe_id <= 0:
        return _bad_request("Invalid recipe ID")

    try:
        user_encrypted = require_user()
    except PermissionError:
        return jsonify({"message": "Unauthorized"}), 401

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
def get_users_rating(recipe_id: int):
    if recipe_id <= 0:
        return _bad_request("Invalid recipe ID")

    try:
        user_encrypted = require_user()
    except PermissionError:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        row = RecipeRating.query.with_entities(RecipeRating.rating).filter_by(
            recipe_id=recipe_id,
            user_encrypted=user_encrypted,
        ).first()

        if not row:
            return jsonify({"usersRating": 0}), 200

        return jsonify({"usersRating": int(row.rating)}), 200

    except Exception as e:
        return jsonify({"message": f"There was an error while fetching users rating. Error: {e}"}), 500