"""
app.py — Automerce
Main Flask application. Contains all routes, session management,
file upload handling, and CSV import logic.
Run with: python app.py
"""

import os
import json
from functools import wraps
from datetime import datetime

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import pandas as pd

import database as db
import automation as auto
import templates_engine as te

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = 'automerce-secret-key-2026'

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialise database and seed defaults on startup
db.init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = db.get_user_by_username(username)

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            flash('Welcome back, {}!'.format(user['username']), 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    stats = db.get_dashboard_stats()
    recent_posts = db.get_all_posts()[:5]
    recent_logs = db.get_all_logs()[:5]
    return render_template('dashboard.html',
                           stats=stats,
                           recent_posts=recent_posts,
                           recent_logs=recent_logs)


# ---------------------------------------------------------------------------
# Products — CRUD
# ---------------------------------------------------------------------------

@app.route('/products')
@login_required
def products():
    all_products = db.get_all_products()
    return render_template('products.html', products=all_products)


@app.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    categories = db.get_all_categories()

    if request.method == 'POST':
        name          = request.form.get('name', '').strip()
        price         = request.form.get('price', 0)
        stock         = request.form.get('stock_quantity', 0)
        description   = request.form.get('description', '').strip()
        category_id   = request.form.get('category_id')
        is_featured   = 1 if request.form.get('is_featured') else 0
        image_path    = None

        # Validate required fields
        if not name or not price:
            flash('Product name and price are required.', 'danger')
            return render_template('add_products.html', categories=categories)

        # Handle image upload
        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Prefix with timestamp to avoid name collisions
            filename = '{}_{}'.format(int(datetime.now().timestamp()), filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = filename

        product_id = db.add_product(
            name=name,
            price=float(price),
            stock_quantity=int(stock),
            description=description,
            image_path=image_path,
            category_id=int(category_id) if category_id else None,
            is_featured=is_featured
        )

        # Log analytics view seed event
        db.log_analytics_event(product_id, 'view')

        # R01 — New Arrival
        auto.detect_and_generate(product_id, 'new_product')

        # R05 — Featured (if checked at creation)
        if is_featured:
            auto.detect_and_generate(
                product_id, 'featured',
                old_data={'is_featured': 0},
                new_data={'is_featured': 1}
            )

        flash('Product "{}" added successfully. Promotional post generated.'.format(name), 'success')
        return redirect(url_for('products'))

    return render_template('add_products.html', categories=categories)


@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product    = db.get_product_by_id(product_id)
    categories = db.get_all_categories()

    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products'))

    if request.method == 'POST':
        name         = request.form.get('name', '').strip()
        price        = float(request.form.get('price', 0))
        stock        = int(request.form.get('stock_quantity', 0))
        description  = request.form.get('description', '').strip()
        category_id  = request.form.get('category_id')
        is_featured  = 1 if request.form.get('is_featured') else 0
        image_path   = product['image_path']  # keep existing unless replaced

        if not name or not price:
            flash('Product name and price are required.', 'danger')
            return render_template('edit_product.html', product=product, categories=categories)

        # Handle image replacement
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = '{}_{}'.format(int(datetime.now().timestamp()), filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = filename

        old_price, old_stock = db.update_product(
            product_id=product_id,
            name=name,
            price=price,
            stock_quantity=stock,
            description=description,
            image_path=image_path,
            category_id=int(category_id) if category_id else None,
            is_featured=is_featured
        )

        # Run automation rules for all changed attributes
        triggered = auto.run_on_edit(
            product_id=product_id,
            old_price=old_price,
            old_stock=old_stock,
            new_price=price,
            new_stock=stock,
            old_featured=product['is_featured'],
            new_featured=is_featured
        )

        if triggered:
            flash('Product updated. Posts generated: {}.'.format(', '.join(triggered)), 'success')
        else:
            flash('Product "{}" updated.'.format(name), 'success')

        return redirect(url_for('products'))

    return render_template('edit_product.html', product=product, categories=categories)


@app.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = db.get_product_by_id(product_id)
    if product:
        db.delete_product(product_id)
        flash('Product "{}" deleted.'.format(product['name']), 'success')
    else:
        flash('Product not found.', 'danger')
    return redirect(url_for('products'))


@app.route('/products/<int:product_id>/view')
@login_required
def view_product(product_id):
    """Record a view analytics event and redirect to products."""
    db.log_analytics_event(product_id, 'view')
    return redirect(url_for('products'))


@app.route('/products/<int:product_id>/interact')
@login_required
def interact_product(product_id):
    """Record an interaction analytics event."""
    db.log_analytics_event(product_id, 'interaction')
    return jsonify({'status': 'ok'})


# ---------------------------------------------------------------------------
# Generated posts — review, edit, approve
# ---------------------------------------------------------------------------

@app.route('/posts')
@login_required
def posts():
    all_posts  = db.get_all_posts()
    templates  = db.get_all_templates()
    return render_template('posts.html', posts=all_posts, templates=templates)


@app.route('/posts/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post      = db.get_post_by_id(post_id)
    templates = db.get_all_templates()

    if not post:
        flash('Post not found.', 'danger')
        return redirect(url_for('posts'))

    if request.method == 'POST':
        content     = request.form.get('content', '').strip()
        template_id = request.form.get('template_id')

        # If admin selected a different template, re-render content from that template
        if template_id:
            rendered = te.render_with_template(post['product_id'], int(template_id))
            if rendered:
                content = rendered

        db.update_post_content(post_id, content)
        flash('Post content updated.', 'success')
        return redirect(url_for('posts'))

    return render_template('edit_post.html', post=post, templates=templates)


@app.route('/posts/approve/<int:post_id>', methods=['POST'])
@login_required
def approve_post(post_id):
    post = db.get_post_by_id(post_id)
    if not post:
        flash('Post not found.', 'danger')
        return redirect(url_for('posts'))

    if not post['content']:
        flash('Cannot approve a post with no content.', 'danger')
        return redirect(url_for('posts'))

    db.approve_post(post_id)
    flash('Post approved successfully.', 'success')
    return redirect(url_for('posts'))


# ---------------------------------------------------------------------------
# Post templates — CRUD
# ---------------------------------------------------------------------------

@app.route('/templates')
@login_required
def templates():
    all_templates = db.get_all_templates()
    post_types = ['New Arrival', 'Price Drop', 'Out of Stock',
                  'Back in Stock', 'Featured Item']
    return render_template('templates.html',
                           templates=all_templates,
                           post_types=post_types)


@app.route('/templates/add', methods=['POST'])
@login_required
def add_template():
    name          = request.form.get('name', '').strip()
    platform      = request.form.get('platform', '').strip()
    template_body = request.form.get('template_body', '').strip()
    post_type     = request.form.get('post_type', '').strip()

    if not name or not template_body or not post_type:
        flash('Name, template body, and post type are required.', 'danger')
    else:
        db.add_template(name, platform, template_body, post_type)
        flash('Template "{}" created.'.format(name), 'success')

    return redirect(url_for('templates'))


@app.route('/templates/edit/<int:template_id>', methods=['GET', 'POST'])
@login_required
def edit_template(template_id):
    template  = db.get_template_by_id(template_id)
    post_types = ['New Arrival', 'Price Drop', 'Out of Stock',
                  'Back in Stock', 'Featured Item']

    if not template:
        flash('Template not found.', 'danger')
        return redirect(url_for('templates'))

    if request.method == 'POST':
        name          = request.form.get('name', '').strip()
        platform      = request.form.get('platform', '').strip()
        template_body = request.form.get('template_body', '').strip()
        post_type     = request.form.get('post_type', '').strip()

        if not name or not template_body or not post_type:
            flash('Name, template body, and post type are required.', 'danger')
        else:
            db.update_template(template_id, name, platform, template_body, post_type)
            flash('Template updated.', 'success')
        return redirect(url_for('templates'))

    return render_template('edit_template.html',
                           template=template,
                           post_types=post_types)


@app.route('/templates/delete/<int:template_id>', methods=['POST'])
@login_required
def delete_template(template_id):
    db.delete_template(template_id)
    flash('Template deleted.', 'success')
    return redirect(url_for('templates'))


# ---------------------------------------------------------------------------
# Analytics dashboard
# ---------------------------------------------------------------------------

@app.route('/analytics')
@login_required
def analytics():
    top_products   = db.get_top_products_by_views(limit=10)
    summary        = db.get_product_analytics_summary()
    cat_dist       = db.get_category_distribution()
    total_views    = db.get_total_views()
    total_interact = db.get_total_interactions()
    total_products = len(db.get_all_products())
    total_posts    = db.get_total_posts_count()

    # Assign performance labels
    labelled = []
    for i, row in enumerate(summary):
        views        = row['views']
        interactions = row['interactions']

        if i == 0 and views > 0:
            label = ('🔥 Trending', 'trending')
        elif interactions == max((r['interactions'] for r in summary), default=0) and interactions > 0:
            label = ('⭐ Top Rated', 'top-rated')
        elif views > 0 and interactions > 0 and i % 4 == 2:
            label = ('💎 Customer Fav.', 'customer-fav')
        elif views > 0 and i % 4 == 3:
            label = ('🚀 Fast Moving', 'fast-moving')
        elif views > 0:
            label = ('🔥 Trending', 'trending')
        else:
            label = ('—', 'none')

        labelled.append({
            'product_id':   row['product_id'],
            'name':         row['name'],
            'category':     row['category_name'] or '—',
            'views':        views,
            'interactions': interactions,
            'label_text':   label[0],
            'label_class':  label[1],
        })

    # Prepare JSON for Chart.js (passed as data attributes)
    chart_labels    = [r['name'] for r in top_products]
    chart_views     = [r['view_count'] for r in top_products]
    donut_labels    = [r['category_name'] for r in cat_dist]
    donut_data      = [r['product_count'] for r in cat_dist]

    return render_template('analytics.html',
                           labelled=labelled,
                           chart_labels=json.dumps(chart_labels),
                           chart_views=json.dumps(chart_views),
                           donut_labels=json.dumps(donut_labels),
                           donut_data=json.dumps(donut_data),
                           total_views=total_views,
                           total_interact=total_interact,
                           total_products=total_products,
                           total_posts=total_posts)


# ---------------------------------------------------------------------------
# CSV import
# ---------------------------------------------------------------------------

@app.route('/import-csv', methods=['GET', 'POST'])
@login_required
def import_csv():
    if request.method == 'POST':
        file = request.files.get('csv_file')

        if not file or not file.filename.endswith('.csv'):
            flash('Please upload a valid CSV file (.csv).', 'danger')
            return redirect(url_for('import_csv'))

        try:
            df = pd.read_csv(file)
        except Exception as e:
            flash('Could not read CSV file: {}'.format(str(e)), 'danger')
            return redirect(url_for('import_csv'))

        required_cols = ['product_name', 'category', 'price',
                         'stock_quantity', 'description']

        if not all(col in df.columns for col in required_cols):
            missing = [c for c in required_cols if c not in df.columns]
            flash('CSV is missing required columns: {}'.format(', '.join(missing)), 'danger')
            return redirect(url_for('import_csv'))

        imported = 0
        errors   = 0

        for _, row in df.iterrows():
            try:
                # Resolve or create category
                cat_name = str(row['category']).strip()
                conn = db.get_db()
                cat_row = conn.execute(
                    "SELECT category_id FROM categories WHERE name = ?", (cat_name,)
                ).fetchone()

                if cat_row:
                    category_id = cat_row['category_id']
                else:
                    c = conn.cursor()
                    c.execute("INSERT INTO categories (name) VALUES (?)", (cat_name,))
                    conn.commit()
                    category_id = c.lastrowid

                conn.close()

                product_id = db.add_product(
                    name=str(row['product_name']).strip(),
                    price=float(row['price']),
                    stock_quantity=int(row['stock_quantity']),
                    description=str(row['description']).strip(),
                    image_path=None,
                    category_id=category_id
                )

                # Trigger R01 for each imported product
                auto.detect_and_generate(product_id, 'new_product')
                imported += 1

            except Exception:
                errors += 1
                continue

        if imported:
            flash('{} product(s) imported successfully.'.format(imported), 'success')
        if errors:
            flash('{} row(s) could not be imported due to errors.'.format(errors), 'warning')

        return redirect(url_for('products'))

    return render_template('import_csv.html')


# ---------------------------------------------------------------------------
# System logs
# ---------------------------------------------------------------------------

@app.route('/logs')
@login_required
def logs():
    all_logs = db.get_all_logs()
    return render_template('logs.html', logs=all_logs)


# ---------------------------------------------------------------------------
# Static file serving for uploaded images
# ---------------------------------------------------------------------------

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)