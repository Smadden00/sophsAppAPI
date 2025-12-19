from ..extensions import db

class RestaurantType(db.Model):
    __tablename__ = "rest_types"

    rest_type_id = db.Column(db.Integer, primary_key=True)
    rest_type = db.Column(db.Text, nullable=False)
