from flask import Blueprint, render_template
from models import Review

reviews = Blueprint('reviews', __name__)

@reviews.route('/reviews')
def index():
    approved_reviews = Review.query.filter_by(is_approved=True).order_by(Review.created_at.desc()).all()
    return render_template('reviews.html', reviews=approved_reviews)
