from flask import Blueprint, redirect, url_for

reviews = Blueprint('reviews', __name__)


@reviews.route('/reviews')
def index():
    return redirect(url_for('main.reviews'))
