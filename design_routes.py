import json
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from werkzeug.utils import secure_filename

import database as db
from auth_helpers import login_required
from services.design_engine import load_template, bulk_generate
from validators import validate_design_template_form

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_background_upload(file_storage):
    if not file_storage or file_storage.filename == '':
        return None
    if not allowed_file(file_storage.filename):
        return None

    filename = secure_filename(file_storage.filename)
    unique_name = f"bg_{os.urandom(8).hex()}_{filename}"
    target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'design_backgrounds')
    os.makedirs(target_dir, exist_ok=True)
    save_path = os.path.join(target_dir, unique_name)
    file_storage.save(save_path)
    return os.path.join('design_backgrounds', unique_name)


designs_bp = Blueprint('designs', __name__)


@designs_bp.route('/designs')
@login_required
def designs():
    templates = db.get_all_design_templates()
    graphics = db.get_all_generated_graphics()
    return render_template('designs.html', templates=templates, graphics=graphics)


@designs_bp.route('/designs/create', methods=['GET', 'POST'])
@login_required
def create_design():
    if request.method == 'POST':
        form_data, errors = validate_design_template_form(request.form)
        background_file = request.files.get('background_image')
        background_path = None

        if background_file and background_file.filename:
            if not allowed_file(background_file.filename):
                errors.append('Background image must be a PNG, JPG, GIF, or WEBP file.')
            else:
                background_path = save_background_upload(background_file)

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('design_form.html', create_mode=True, form_data=form_data)

        template_id = db.save_design_template(
            form_data['name'],
            form_data['platform'],
            background_path,
            form_data['layout_json'],
        )
        flash('Design template saved successfully.', 'success')
        return redirect(url_for('designs.designs'))

    default_layout = json.dumps({
        'product_image': {
            'x': 620,
            'y': 60,
            'width': 480,
            'height': 480
        },
        'placeholders': [
            {'type': 'product_name', 'x': 60, 'y': 60, 'font_size': 42, 'color': '#ffffff'},
            {'type': 'price', 'x': 60, 'y': 120, 'font_size': 34, 'color': '#ffffff'},
            {'type': 'description', 'x': 60, 'y': 180, 'font_size': 22, 'color': '#ffffff', 'max_width': 520},
        ]
    }, indent=2)
    return render_template('design_form.html', create_mode=True, form_data={'layout_json': default_layout})


@designs_bp.route('/designs/edit/<int:template_id>', methods=['GET', 'POST'])
@login_required
def edit_design(template_id):
    template = db.get_design_template_by_id(template_id)
    if not template:
        flash('Design template not found.', 'danger')
        return redirect(url_for('designs.designs'))

    if request.method == 'POST':
        form_data, errors = validate_design_template_form(request.form)
        background_path = None
        background_file = request.files.get('background_image')

        if background_file and background_file.filename:
            if not allowed_file(background_file.filename):
                errors.append('Background image must be a PNG, JPG, GIF, or WEBP file.')
            else:
                background_path = save_background_upload(background_file)

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('design_form.html', create_mode=False, template=template, form_data=form_data)

        db.update_design_template(
            template_id,
            form_data['name'],
            form_data['platform'],
            background_path,
            form_data['layout_json'],
        )
        flash('Design template updated successfully.', 'success')
        return redirect(url_for('designs.designs'))

    form_data = {
        'name': template['name'],
        'platform': template['platform'],
        'layout_json': template['layout_json'] or '{}',
    }
    return render_template('design_form.html', create_mode=False, template=template, form_data=form_data)


@designs_bp.route('/designs/delete/<int:template_id>', methods=['POST'])
@login_required
def delete_design(template_id):
    db.delete_design_template(template_id)
    flash('Design template deleted.', 'success')
    return redirect(url_for('designs.designs'))


@designs_bp.route('/graphics')
@login_required
def graphics():
    graphics = db.get_all_generated_graphics()
    return render_template('graphics.html', graphics=graphics)


@designs_bp.route('/graphics/generate', methods=['GET', 'POST'])
@login_required
def generate_graphics():
    templates = db.get_all_design_templates()
    products = db.get_all_products()

    if request.method == 'POST':
        template_id = request.form.get('template_id')
        selected_products = request.form.getlist('product_ids')

        if not template_id:
            flash('Please select a design template.', 'danger')
            return render_template('graphics_generate.html', templates=templates, products=products)
        if not selected_products:
            flash('Please choose at least one product to generate graphics.', 'danger')
            return render_template('graphics_generate.html', templates=templates, products=products)

        generated_ids = bulk_generate(int(template_id), selected_products)
        if generated_ids:
            flash(f'Generated {len(generated_ids)} graphic(s).', 'success')
            return redirect(url_for('designs.graphics'))

        flash('No graphics were generated. Check your template and selected products.', 'warning')

    return render_template('graphics_generate.html', templates=templates, products=products)


@designs_bp.route('/graphics/view/<int:graphic_id>')
@login_required
def view_graphic(graphic_id):
    graphic = db.get_generated_graphic_by_id(graphic_id)
    if not graphic:
        flash('Graphic not found.', 'danger')
        return redirect(url_for('designs.graphics'))
    return render_template('graphic_view.html', graphic=graphic)


@designs_bp.route('/graphics/download/<int:graphic_id>')
@login_required
def download_graphic(graphic_id):
    graphic = db.get_generated_graphic_by_id(graphic_id)
    if not graphic or not graphic['image_path']:
        flash('Graphic not found.', 'danger')
        return redirect(url_for('designs.graphics'))

    image_path = graphic['image_path'].replace('\\', '/')
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        image_path,
        as_attachment=True,
        mimetype='image/png'
    )
