# app/models/recipe.py
from __future__ import annotations

from ..extensions import db

class Recipe(db.Model):
    __tablename__ = "recipes"

    recipe_id = db.Column(db.Integer, primary_key=True)
    recipe_name = db.Column(db.Text, nullable=False)
    user_encrypted = db.Column(db.String(64), nullable=False)

    # NOTE: your DB DDL says "prep_time" but your Next.js uses "prep_time_in_min".
    # This model uses the DDL column name: prep_time
    prep_time = db.Column(db.Integer, nullable=False)

    # DB DDL includes rating numeric(3,1) not null (0..10). You’re also computing avg rating from recipe_ratings.
    # Keep the column, but your endpoint uses AVG(recipe_ratings.rating) for averageRating.
    rating = db.Column(db.Numeric(3, 1), nullable=False)

    meal = db.Column(db.Text, nullable=True)
    rec_img_url = db.Column(db.Text, nullable=True)

    # Optional: if you have this column in your real schema (your Next.js selects soph_submitted)
    soph_submitted = db.Column(db.Boolean, nullable=True)

class RecipeComment(db.Model):
    __tablename__ = "recipescomments"  # Postgres lowercases unquoted identifiers; adjust if your table is actually "recipesComments"
    comment_id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.recipe_id", ondelete="CASCADE"), nullable=False)
    comment = db.Column(db.String(150), nullable=False)
    user_encrypted = db.Column(db.String(64), nullable=False)

class RecipeInstruction(db.Model):
    __tablename__ = "recipe_instructions"
    instruction_id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.recipe_id", ondelete="CASCADE"), nullable=False)
    instruction_order = db.Column(db.Integer, nullable=False)
    instruction = db.Column(db.Text, nullable=False)

class RecipeIngredient(db.Model):
    __tablename__ = "recipe_ingredients"
    ingredient_id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.recipe_id"), nullable=False)
    ingredient = db.Column(db.Text, nullable=False)

class RecipeRating(db.Model):
    __tablename__ = "recipe_ratings"
    rating_id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.recipe_id", ondelete="CASCADE"), nullable=False)
    user_encrypted = db.Column(db.String(64), nullable=False)
    rating = db.Column(db.SmallInteger, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("recipe_id", "user_encrypted", name="unique_user_recipe_rating"),
        db.Index("idx_recipe_ratings_recipe_id", "recipe_id"),
        db.Index("idx_recipe_ratings_user", "user_encrypted"),
    )