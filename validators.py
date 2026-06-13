import html


def sanitize_text(value):
    if value is None:
        return ''
    return html.escape(str(value).strip())


def validate_price(value):
    if value is None or str(value).strip() == '':
        raise ValueError('Price is required.')
    try:
        price = float(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError('Price must be a valid number.')
    if price < 0:
        raise ValueError('Price cannot be negative.')
    return price


def validate_stock(value):
    if value is None or str(value).strip() == '':
        return 0
    try:
        stock = int(float(str(value).strip()))
    except (TypeError, ValueError):
        raise ValueError('Stock quantity must be a valid integer.')
    if stock < 0:
        raise ValueError('Stock quantity cannot be negative.')
    return stock


def validate_product_form(data):
    errors = []
    name = sanitize_text(data.get('name'))
    description = sanitize_text(data.get('description'))
    location = sanitize_text(data.get('location'))
    category_id = data.get('category_id')

    if category_id is not None:
        category_id = str(category_id).strip()
        category_id = int(category_id) if category_id else None

    try:
        price = validate_price(data.get('price'))
    except ValueError as exc:
        errors.append(str(exc))
        price = None

    try:
        stock_quantity = validate_stock(data.get('stock_quantity'))
    except ValueError as exc:
        errors.append(str(exc))
        stock_quantity = None

    if not name:
        errors.append('Product name is required.')

    return {
        'name': name,
        'price': price,
        'stock_quantity': stock_quantity,
        'description': description,
        'location': location,
        'category_id': category_id,
        'is_featured': 1 if data.get('is_featured') else 0,
    }, errors


def validate_template_form(data):
    errors = []
    name = sanitize_text(data.get('name'))
    platform = sanitize_text(data.get('platform'))
    template_body = str(data.get('template_body') or '').strip()
    post_type = sanitize_text(data.get('post_type'))

    if not name:
        errors.append('Template name is required.')
    if not template_body:
        errors.append('Template body is required.')
    if not post_type:
        errors.append('Post type is required.')

    return {
        'name': name,
        'platform': platform,
        'template_body': template_body,
        'post_type': post_type,
    }, errors


def validate_design_template_form(data):
    errors = []
    name = sanitize_text(data.get('name'))
    platform = sanitize_text(data.get('platform'))
    layout_json = str(data.get('layout_json') or '').strip()

    if not name:
        errors.append('Design template name is required.')
    if not layout_json:
        errors.append('Layout JSON is required.')
    else:
        try:
            import json
            parsed = json.loads(layout_json)
            if not isinstance(parsed, dict):
                errors.append('Layout JSON must be an object.')
        except Exception:
            errors.append('Layout JSON must be valid JSON.')

    return {
        'name': name,
        'platform': platform,
        'layout_json': layout_json,
    }, errors


def validate_csv_row(row):
    errors = []
    product_name = sanitize_text(row.get('product_name'))
    category = sanitize_text(row.get('category'))
    description = sanitize_text(row.get('description'))

    try:
        price = validate_price(row.get('price'))
    except ValueError as exc:
        errors.append(str(exc))
        price = None

    try:
        stock_quantity = validate_stock(row.get('stock_quantity'))
    except ValueError as exc:
        errors.append(str(exc))
        stock_quantity = None

    if not product_name:
        errors.append('Product name is required.')
    if not category:
        errors.append('Category is required.')
    if description == '':
        errors.append('Description is required.')

    return {
        'product_name': product_name,
        'category': category,
        'price': price,
        'stock_quantity': stock_quantity,
        'description': description,
    }, errors
