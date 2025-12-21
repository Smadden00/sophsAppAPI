from flask import Flask, jsonify
from .config import Config
from .extensions import db, cors
from .utils.validator import Auth0JWTBearerTokenValidator
from authlib.integrations.flask_oauth2 import ResourceProtector
import os

# Auth0 - define at module level so it can be imported
require_auth = ResourceProtector()
validator = Auth0JWTBearerTokenValidator(
    os.environ.get('AUTH0_DOMAIN'),
    os.environ.get('AUTH0_API_IDENTIFIER'),
)
require_auth.register_token_validator(validator)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
        
    cors.init_app(
        app, 
        resources={
            r"/api/*": {
                "origins": ["http://localhost:3000", "http://127.0.0.1:3000", "https://sophsdatabasedomain.duckdns.org", "https://sophsmenu.com"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "x-api-key", "Authorization"]
            }},
        supports_credentials=True,
    )

    # Import models so SQLAlchemy knows them
    from . import models

    # Register blueprints
    from .routes.recipes import bp as recipes_bp
    from .routes.restaurant_types import bp as restaurant_types_bp
    from .routes.reviews import bp as reviews_bp

    app.register_blueprint(recipes_bp, url_prefix="/api/recipes")
    app.register_blueprint(restaurant_types_bp, url_prefix="/api/restaurant-types")
    app.register_blueprint(reviews_bp, url_prefix="/api/reviews")

    @app.get("/api/health")
    def health():
        db.session.execute(db.text("SELECT 1"))
        return jsonify(status="ok")

    return app