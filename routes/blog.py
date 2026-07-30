from flask import Blueprint, render_template
from models import BlogPost

blog = Blueprint('blog', __name__)

@blog.route('/blog')
def index():
    posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.is_featured.desc(), BlogPost.created_at.desc()).all()
    return render_template('blog.html', posts=posts)

@blog.route('/blog/<slug>')
def detail(slug):
    post = BlogPost.query.filter_by(slug=slug, is_published=True).first_or_404()
    recent_posts = BlogPost.query.filter(BlogPost.id != post.id, BlogPost.is_published == True).order_by(BlogPost.created_at.desc()).limit(3).all()
    return render_template('blog_detail.html', post=post, recent_posts=recent_posts)
