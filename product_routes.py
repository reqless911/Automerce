from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app

import automation as auto
import database as db
from auth_helpers import login_required
from services.csv_service import import_csv_products
from services.upload_service import save_uploaded_image
from validators import validate_product_form

products_bp = Blueprint('products', __name__)


@products_bp.route('/products')
@login_required
def products():
    all_products = db.get_all_products()
    return render_template('products.html', products=all_products)


@products_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    categories = db.get_all_categories()

    if request.method == 'POST':
        form_data, errors = validate_product_form(request.form)
        image_path = None

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('add_products.html', categories=categories)

        file = request.files.get('image')
        image_path = save_uploaded_image(
            file,
            current_app.config['UPLOAD_FOLDER'],
            current_app.config['ALLOWED_EXTENSIONS'],
        )

        product_id = db.add_product(
            name=form_data['name'],
            price=form_data['price'],
            stock_quantity=form_data['stock_quantity'],
            description=form_data['description'],
            image_path=image_path,
            category_id=form_data['category_id'],
            is_featured=form_data['is_featured'],
        )

        db.log_analytics_event(product_id, 'view')

        try:
            auto.detect_and_generate(product_id, 'new_product')
            if form_data['is_featured']:
                auto.detect_and_generate(
                    product_id,
                    'featured',
                    old_data={'is_featured': 0},
                    new_data={'is_featured': 1},
                )
        except Exception as exc:
            db.log_action(None, 'Automation failure', f'new_product:{exc}')
            flash('Product added, but automation failed to generate promotional posts.', 'warning')
            return redirect(url_for('products.products'))

        flash('Product "{}" added successfully. Promotional post generated.'.format(form_data['name']), 'success')
        return redirect(url_for('products.products'))

    return render_template('add_products.html', categories=categories)


@products_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = db.get_product_by_id(product_id)
    categories = db.get_all_categories()

    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.products'))

    if request.method == 'POST':
        form_data, errors = validate_product_form(request.form)
        image_path = product['image_path']

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('edit_product.html', product=product, categories=categories)

        file = request.files.get('image')
        new_image_path = save_uploaded_image(
            file,
            current_app.config['UPLOAD_FOLDER'],
            current_app.config['ALLOWED_EXTENSIONS'],
        )
        if new_image_path:
            image_path = new_image_path

        old_price, old_stock = db.update_product(
            product_id=product_id,
            name=form_data['name'],
            price=form_data['price'],
            stock_quantity=form_data['stock_quantity'],
            description=form_data['description'],
            image_path=image_path,
            category_id=form_data['category_id'],
            is_featured=form_data['is_featured'],
        )

        triggered = []
        try:
            triggered = auto.run_on_edit(
                product_id=product_id,
                old_price=old_price,
                old_stock=old_stock,
                new_price=form_data['price'],
                new_stock=form_data['stock_quantity'],
                old_featured=product['is_featured'],
                new_featured=form_data['is_featured'],
            )
        except Exception as exc:
            db.log_action(None, 'Automation failure', f'edit_product:{exc}')
            flash('Product updated, but automation failed to process changes.', 'warning')
            return redirect(url_for('products.products'))

        if triggered:
            flash('Product updated. Posts generated: {}.'.format(', '.join(triggered)), 'success')
        else:
            flash('Product "{}" updated.'.format(form_data['name']), 'success')

        return redirect(url_for('products.products'))

    return render_template('edit_product.html', product=product, categories=categories)


@products_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = db.get_product_by_id(product_id)
    if product:
        db.delete_product(product_id)
        flash('Product "{}" deleted.'.format(product['name']), 'success')
    else:
        flash('Product not found.', 'danger')
    return redirect(url_for('products.products'))


@products_bp.route('/products/<int:product_id>/view')
@login_required
def view_product(product_id):
    db.log_analytics_event(product_id, 'view')
    return redirect(url_for('products.products'))


@products_bp.route('/products/<int:product_id>/interact')
@login_required
def interact_product(product_id):
    db.log_analytics_event(product_id, 'interaction')
    return jsonify({'status': 'ok'})


@products_bp.route('/import-csv', methods=['GET', 'POST'])
@login_required
def import_csv():
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or not file.filename.lower().endswith('.csv'):
            flash('Please upload a valid CSV file (.csv).', 'danger')
            return redirect(url_for('products.import_csv'))

        try:
            imported_ids, parse_errors = import_csv_products(file)
        except Exception as exc:
            flash(f'Could not read CSV file: {exc}', 'danger')
            return redirect(url_for('products.import_csv'))

        imported = len(imported_ids)
        failed = len(parse_errors)

        for product_id in imported_ids:
            try:
                auto.detect_and_generate(product_id, 'new_product')
            except Exception as exc:
                db.log_action(None, 'Automation failure', f'csv_import_new_product:{exc}')

        if imported:
            flash(f'{imported} product(s) imported successfully.', 'success')
        if failed:
            flash(f'{failed} row(s) could not be imported due to validation errors.', 'warning')

        return redirect(url_for('products.products'))

    return render_template('import_csv.html')
