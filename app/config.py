import os

class Config:
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{os.environ["PGUSER"]}:{os.environ["PGPASSWORD"]}@127.0.0.1:{os.environ["PGPORT"]}/{os.environ["PGDATABASE"]}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False