import os

class Config:
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{os.environ["PGUSER"]}:{os.environ["PGPASSWORD"]}@127.0.0.1:{os.environ["PGPORT"]}/{os.environ["PGDATABASE"]}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 50MB upload limit
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024