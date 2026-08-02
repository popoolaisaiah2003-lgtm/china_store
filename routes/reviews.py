from flask import Blueprint, render_template
from models import Review

reviews = Blueprint('reviews', __name__)

REVIEW_COUNTRY_MAP = {
    'Dr. Anna Becker': 'Germany',
    'Sofia Martinez': 'Spain',
    'Dr. James Caldwell': 'United States',
    'Luca Romano': 'Italy',
    'Dr. Priya Nair': 'India',
    'Noah Williams': 'Canada',
    'Yuki Tanaka': 'Japan',
    'Omar Hassan': 'UAE'
}

@reviews.route('/reviews')
def index():
    approved_reviews = Review.query.filter_by(is_approved=True).order_by(Review.created_at.desc()).all()
    reviews_data = [
        {
            'name': r.reviewer_name,
            'country': REVIEW_COUNTRY_MAP.get(r.reviewer_name, 'International Client'),
            'rating': r.rating or 5,
            'comment': r.comment,
            'verified': True,
            'created_at': r.created_at
        }
        for r in approved_reviews
    ]
    return render_template('reviews.html', reviews=reviews_data)
