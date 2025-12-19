from ..extensions import db


class Review(db.Model):
    __tablename__ = "reviews"

    review_id = db.Column(db.Integer, primary_key=True)

    rest_name = db.Column(db.Text, nullable=False)
    o_rating = db.Column(db.Numeric(3, 1), nullable=False)   # 1..10 (match your usage)
    price = db.Column(db.Integer, nullable=False)            # 1..4
    taste = db.Column(db.Numeric(3, 1), nullable=False)      # 1..10
    experience = db.Column(db.Numeric(3, 1), nullable=False) # 1..10
    description = db.Column(db.Text, nullable=True)

    city = db.Column(db.Text, nullable=False)
    state_code = db.Column(db.Text, nullable=False)

    soph_submitted = db.Column(db.Boolean, nullable=True)
    user_encrypted = db.Column(db.String(64), nullable=False)


class RestTypeReviewRef(db.Model):
    """
    Junction table between rest_types and reviews.
    """
    __tablename__ = "rest_type_review_ref"

    # If your junction table has its own PK column, change this accordingly.
    rest_type_id = db.Column(
        db.Integer,
        db.ForeignKey("rest_types.rest_type_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    review_id = db.Column(
        db.Integer,
        db.ForeignKey("reviews.review_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )