# app/models/city.py
from ..extensions import db

class City(db.Model):
    __tablename__ = "cities"

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.Text, nullable=False)
    state_code = db.Column(db.Text, nullable=False, index=True)

    def to_dict(self):
        return {
            "city": self.city,
            "state": self.state_code,
        }
