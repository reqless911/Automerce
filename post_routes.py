from flask import Blueprint, render_template, request, redirect, url_for, flash

import database as db
import templates_engine as te
from auth_helpers import login_required
from validators import validate_template_form

posts_bp = Blueprint('posts', __name__)


@posts_bp.route('/posts')
@login_required
def posts():
    all_posts = db.get_all_posts()
    templates = db.get_all_templates()
    return render_template('posts.html', posts=all_posts, templates=templates)


@posts_bp.route('/posts/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = db.get_post_by_id(post_id)
    templates = db.get_all_templates()

    if not post:
        flash('Post not found.', 'danger')
        return redirect(url_for('posts.posts'))

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        template_id = request.form.get('template_id')

        if template_id:
            rendered = te.render_with_template(post['product_id'], int(template_id))
            if rendered:
                content = rendered

        db.update_post_content(post_id, content)
        flash('Post content updated.', 'success')
        return redirect(url_for('posts.posts'))

    return render_template('edit_post.html', post=post, templates=templates)


@posts_bp.route('/posts/approve/<int:post_id>', methods=['POST'])
@login_required
def approve_post(post_id):
    post = db.get_post_by_id(post_id)
    if not post:
        flash('Post not found.', 'danger')
        return redirect(url_for('posts.posts'))

    if not post['content']:
        flash('Cannot approve a post with no content.', 'danger')
        return redirect(url_for('posts.posts'))

    db.approve_post(post_id)
    flash('Post approved successfully.', 'success')
    return redirect(url_for('posts.posts'))


@posts_bp.route('/templates')
@login_required
def templates():
    all_templates = db.get_all_templates()
    post_types = ['New Arrival', 'Price Drop', 'Out of Stock', 'Back in Stock', 'Featured Item']
    return render_template('templates.html', templates=all_templates, post_types=post_types)


@posts_bp.route('/templates/add', methods=['POST'])
@login_required
def add_template():
    cleaned_data, errors = validate_template_form(request.form)
    if errors:
        for error in errors:
            flash(error, 'danger')
    else:
        db.add_template(
            cleaned_data['name'],
            cleaned_data['platform'],
            cleaned_data['template_body'],
            cleaned_data['post_type'],
        )
        flash(f'Template "{cleaned_data["name"]}" created.', 'success')
    return redirect(url_for('posts.templates'))


@posts_bp.route('/templates/edit/<int:template_id>', methods=['GET', 'POST'])
@login_required
def edit_template(template_id):
    template = db.get_template_by_id(template_id)
    post_types = ['New Arrival', 'Price Drop', 'Out of Stock', 'Back in Stock', 'Featured Item']

    if not template:
        flash('Template not found.', 'danger')
        return redirect(url_for('posts.templates'))

    if request.method == 'POST':
        cleaned_data, errors = validate_template_form(request.form)
        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            db.update_template(
                template_id,
                cleaned_data['name'],
                cleaned_data['platform'],
                cleaned_data['template_body'],
                cleaned_data['post_type'],
            )
            flash('Template updated.', 'success')
        return redirect(url_for('posts.templates'))

    return render_template('edit_template.html', template=template, post_types=post_types)


@posts_bp.route('/templates/delete/<int:template_id>', methods=['POST'])
@login_required
def delete_template(template_id):
    db.delete_template(template_id)
    flash('Template deleted.', 'success')
    return redirect(url_for('posts.templates'))
