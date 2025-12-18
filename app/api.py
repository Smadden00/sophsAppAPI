import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy

def create_app():
    app = Flask(__name__)
    databaseURL = f"postgresql+psycopg2://{os.environ["PGUSER"]}:{os.environ["PGPASSWORD"]}@127.0.0.1:{os.environ["PGPORT"]}/{os.environ["PGDATABASE"]}"
    app.config["SQLALCHEMY_DATABASE_URI"] = databaseURL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    ##################
    # Health Checks
    ##################
    @app.get("/health")
    def health_check():
        return jsonify(status="ok"), 200

    @app.get("/hello")
    def hello_test():
        name = request.args.get("name", "World")
        return jsonify(message=f"Hello, {name}!")

#Setup
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)