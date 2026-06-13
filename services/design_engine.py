import json
import os
import uuid
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

import database as db

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
BACKGROUND_DIR = os.path.join(UPLOAD_DIR, 'design_backgrounds')
GRAPHICS_DIR = os.path.join(UPLOAD_DIR, 'graphics')

for path in (UPLOAD_DIR, BACKGROUND_DIR, GRAPHICS_DIR):
    os.makedirs(path, exist_ok=True)

PLACEHOLDER_KEYS = {
    'product_name': 'name',
    'price': 'price',
    'description': 'description',
    'category': 'category_name',
    'location': 'location',
    'floor': 'location',
}

DEFAULT_LAYOUT = {
    'placeholders': [
        {
            'type': 'product_name',
            'x': 60,
            'y': 60,
            'font_size': 40,
            'color': '#ffffff',
        },
        {
            'type': 'price',
            'x': 60,
            'y': 120,
            'font_size': 28,
            'color': '#ffffff',
        },
        {
            'type': 'description',
            'x': 60,
            'y': 180,
            'font_size': 22,
            'color': '#ffffff',
            'max_width': 600,
        },
    ],
    'product_image': {
        'x': 620,
        'y': 60,
        'width': 480,
        'height': 480,
        'radius': 20,
    },
}


def _get_font(size=28):
    try:
        return ImageFont.truetype('arial.ttf', size)
    except Exception:
        try:
            return ImageFont.truetype('DejaVuSans.ttf', size)
        except Exception:
            return ImageFont.load_default()


def _wrap_text(text, font, max_width, draw):
    words = text.split()
    lines = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        width, _ = _text_size(candidate, font)
        if width <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _get_value(source, key):
    if hasattr(source, 'get'):
        return source.get(key)
    try:
        return source[key]
    except Exception:
        return None


def _text_size(text, font):
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _load_image(path, size=None, color=(255, 255, 255, 255)):
    if not path or not os.path.isfile(path):
        img = Image.new('RGBA', size or (1200, 1200), color)
        return img

    img = Image.open(path).convert('RGBA')
    if size:
        img.thumbnail(size, Image.LANCZOS)
    return img


def _compose_image(template, product, layout):
    bg_path = os.path.join(UPLOAD_DIR, template['background_image']) if template['background_image'] else None
    base = _load_image(bg_path, size=None, color=(24, 24, 24, 255))
    if base is None:
        base = Image.new('RGBA', (1200, 1200), (24, 24, 24, 255))
    draw = ImageDraw.Draw(base)

    product_image_info = layout.get('product_image', {})
    if product_image_info:
        box_w = product_image_info.get('width', 400)
        box_h = product_image_info.get('height', 400)
        product_img_path = os.path.join(UPLOAD_DIR, _get_value(product, 'image_path')) if _get_value(product, 'image_path') else None
        product_img = _load_image(product_img_path, size=(box_w, box_h), color=(230, 230, 230, 255))

        if product_img:
            target = Image.new('RGBA', (box_w, box_h), (0, 0, 0, 0))
            target.paste(product_img, ((box_w - product_img.width) // 2, (box_h - product_img.height) // 2), product_img)
            base.paste(target, (product_image_info.get('x', 60), product_image_info.get('y', 180)), target)

    for placeholder in layout.get('placeholders', []):
        ptype = placeholder.get('type')
        if ptype == 'product_image':
            continue
        font_size = placeholder.get('font_size', 28)
        font = _get_font(font_size)
        color = placeholder.get('color', '#ffffff')
        x = int(placeholder.get('x', 60))
        y = int(placeholder.get('y', 60))
        max_width = placeholder.get('max_width')

        if ptype == 'price':
            price_value = _get_value(product, 'price')
            if price_value is None:
                visual = ''
            else:
                try:
                    visual = f"KES {float(price_value):,.0f}"
                except (TypeError, ValueError):
                    visual = str(price_value)
        else:
            field = PLACEHOLDER_KEYS.get(ptype)
            if field:
                visual = str(_get_value(product, field) or '')
            else:
                visual = str(_get_value(product, ptype) or '')
        lines = [visual]
        if max_width:
            lines = _wrap_text(visual, font, max_width, draw)

        for line in lines:
            draw.text((x, y), line, font=font, fill=color)
            y += _text_size(line, font)[1] + 6

    return base


def load_template(template_id):
    template = db.get_design_template_by_id(template_id)
    if not template:
        return None

    layout = {}
    try:
        layout = json.loads(template['layout_json'] or '{}')
    except Exception:
        layout = {}

    if not isinstance(layout, dict):
        layout = {}

    return {
        'template_id': template['template_id'],
        'name': template['name'],
        'platform': template['platform'],
        'background_image': template['background_image'],
        'layout_json': template['layout_json'],
        'layout': layout,
    }


def render_product(template_id, product_id):
    design_template = load_template(template_id)
    if not design_template:
        return None

    product = db.get_product_by_id(product_id)
    if not product:
        return None

    layout = design_template['layout'] or DEFAULT_LAYOUT
    image = _compose_image(design_template, product, layout)

    file_name = f"graphic_{product_id}_{template_id}_{uuid.uuid4().hex[:8]}.png"
    relative_path = os.path.join('graphics', file_name).replace('\\', '/')
    target_path = os.path.join(GRAPHICS_DIR, file_name)

    image.save(target_path, format='PNG')
    graphic_id = save_graphic(product_id, template_id, relative_path)

    return {
        'graphic_id': graphic_id,
        'image_path': relative_path,
    }


def bulk_generate(template_id, product_ids):
    generated_ids = []
    for pid in product_ids:
        try:
            result = render_product(template_id, int(pid))
            if result:
                generated_ids.append(result['graphic_id'])
        except Exception:
            continue
    return generated_ids


def save_graphic(product_id, template_id, image_path):
    return db.save_generated_graphic(product_id, template_id, image_path)
