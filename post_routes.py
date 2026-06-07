from flask import Blueprint, render_template, request, redirect, url_for, flash, Response

import database as db
import templates_engine as te
from auth_helpers import login_required
from services.post_service import create_post as create_generated_post, get_post_with_product, update_post, generate_export_html
from validators import validate_template_form

posts_bp = Blueprint('posts', __name__)


@posts_bp.route('/posts')
@login_required
def posts():
    all_posts = db.get_all_posts()
    templates = db.get_all_templates()
    return render_template('posts.html', posts=all_posts, templates=templates)


@posts_bp.route('/posts/create/<int:product_id>', methods=['GET', 'POST'])
@login_required
def create_post(product_id):
    product = db.get_product_by_id(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.products'))

    templates = db.get_all_templates()
    if not templates:
        flash('No templates available. Create a template first.', 'danger')
        return redirect(url_for('posts.templates'))

    preview_by_template = {
        template['template_id']: te.render_with_template(product_id, template['template_id']) or ''
        for template in templates
    }

    selected_template_id = request.form.get('template_id')
    selected_template_id = int(selected_template_id) if selected_template_id else templates[0]['template_id']
    caption = request.form.get('caption', '') if request.method == 'POST' else ''
    content = preview_by_template.get(selected_template_id, preview_by_template[templates[0]['template_id']])

    if request.method == 'POST':
        try:
            created = create_generated_post(product_id, int(selected_template_id), caption)
        except Exception:
            created = None

        if not created:
            flash('Could not create the post. Please try again.', 'danger')
            return render_template(
                'edit_post.html',
                create_mode=True,
                product=product,
                templates=templates,
                selected_template_id=int(selected_template_id),
                preview_by_template=preview_by_template,
                caption=caption,
                content=content,
                form_action=url_for('posts.create_post', product_id=product_id),
            )

        flash('Marketing post created successfully.', 'success')
        return redirect(url_for('posts.edit_post', post_id=created['post_id']))

    return render_template(
        'edit_post.html',
        create_mode=True,
        product=product,
        templates=templates,
        selected_template_id=int(selected_template_id),
        preview_by_template=preview_by_template,
        caption=caption,
        content=content,
        form_action=url_for('posts.create_post', product_id=product_id),
    )


@posts_bp.route('/posts/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = get_post_with_product(post_id)
    templates = db.get_all_templates()

    if not post:
        flash('Post not found.', 'danger')
        return redirect(url_for('posts.posts'))

    preview_by_template = {
        template['template_id']: te.render_with_template(post['product_id'], template['template_id']) or ''
        for template in templates
    }

    selected_template_id = request.form.get('template_id') if request.method == 'POST' else post['template_id']
    selected_template_id = int(selected_template_id) if selected_template_id else (templates[0]['template_id'] if templates else None)
    caption = request.form.get('caption', post['caption'] or '') if request.method == 'POST' else post['caption'] or ''
    content = request.form.get('content', post['content'] or '') if request.method == 'POST' else post['content'] or ''

    if request.method == 'POST':
        updated = update_post(post_id, caption, content, selected_template_id)
        if updated:
            flash('Post updated successfully.', 'success')
            return redirect(url_for('posts.edit_post', post_id=post_id))
        flash('Could not update the post. Please try again.', 'danger')

    return render_template(
        'edit_post.html',
        post=post,
        templates=templates,
        selected_template_id=selected_template_id,
        preview_by_template=preview_by_template,
        caption=caption,
        content=content,
        form_action=url_for('posts.edit_post', post_id=post_id),
    )


@posts_bp.route('/posts/export/<int:post_id>')
@login_required
def export_post(post_id):
    html_content = generate_export_html(post_id)
    if not html_content:
        flash('Post not found.', 'danger')
        return redirect(url_for('posts.posts'))
    return Response(html_content, mimetype='text/html')


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
