from flask import Flask, jsonify
from .config import Config
from .extensions import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Import models so SQLAlchemy knows them (important)
    from . import models  # noqa: F401

    # Register blueprints
    from .routes.cities import bp as cities_bp
    from .routes.recipes import bp as recipes_bp
    from .routes.restaurant_types import bp as restaurant_types_bp
    from .routes.reviews import bp as reviews_bp

    app.register_blueprint(cities_bp, url_prefix="/api/cities")
    app.register_blueprint(recipes_bp, url_prefix="/api/recipes")
    app.register_blueprint(restaurant_types_bp, url_prefix="/api/restaurant-types")
    app.register_blueprint(reviews_bp, url_prefix="/api/reviews")

    @app.get("/api/health")
    def health():
        db.session.execute(db.text("SELECT 1"))
        return jsonify(status="ok")

    return app