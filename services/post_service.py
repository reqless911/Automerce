import html
from jinja2 import Environment, BaseLoader

import database as db
import templates_engine as te

STYLE_TEMPLATES = {
    'whatsapp': {
        'title': 'WhatsApp Post Export',
        'background': '#111',
        'card': '#1a1a1a',
        'text': '#f8f9fa',
        'accent': '#25d366',
        'caption_label': 'Caption',
    },
    'instagram': {
        'title': 'Instagram Post Export',
        'background': '#fdfdfd',
        'card': '#ffffff',
        'text': '#212529',
        'accent': '#e1306c',
        'caption_label': 'Caption',
    },
    'facebook marketplace': {
        'title': 'Facebook Marketplace Export',
        'background': '#f3f6fb',
        'card': '#ffffff',
        'text': '#1c1e21',
        'accent': '#1877f2',
        'caption_label': 'Caption',
    },
    'html': {
        'title': 'Marketing Post Export',
        'background': '#f8f9fa',
        'card': '#ffffff',
        'text': '#212529',
        'accent': '#0d6efd',
        'caption_label': 'Caption',
    },
}

EXPORT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            margin: 0;
            min-height: 100vh;
            background: {{ background }};
            color: {{ text }};
            font-family: Inter, system-ui, sans-serif;
        }

        .page-shell {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 2rem;
        }

        .post-card {
            max-width: 700px;
            width: 100%;
            border-radius: 24px;
            background: {{ card }};
            box-shadow: 0 24px 64px rgba(0,0,0,0.12);
            padding: 2rem;
            border: 1px solid rgba(0,0,0,0.06);
        }

        .post-meta {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }

        .post-meta strong {
            color: {{ accent }};
        }

        .post-caption {
            margin-bottom: 1.2rem;
            padding: 1rem;
            border-radius: 18px;
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.16);
            white-space: pre-wrap;
        }

        .post-body {
            line-height: 1.75;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .post-footer {
            margin-top: 2rem;
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 1rem;
            font-size: 0.95rem;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="page-shell">
        <div class="post-card">
            <div class="post-meta">
                <div>
                    <div><strong>{{ product_name }}</strong></div>
                    <div>{{ template_name or 'Custom Template' }}</div>
                </div>
                <div>
                    <div>{{ label }}</div>
                    <div>{{ export_format_display }}</div>
                </div>
            </div>
            {% if caption %}
            <div class="post-caption">
                <strong>{{ caption_label }}:</strong>
                <div>{{ caption }}</div>
            </div>
            {% endif %}
            <div class="post-body">{{ content }}</div>
            <div class="post-footer">
                <span>Created: {{ created_at }}</span>
                <span>Export style: {{ export_format_display }}</span>
            </div>
        </div>
    </div>
</body>
</html>
"""


def _normalize_format(value):
    if not value:
        return 'html'
    normalized = value.strip().lower()
    if normalized in STYLE_TEMPLATES:
        return normalized
    if 'whatsapp' in normalized:
        return 'whatsapp'
    if 'instagram' in normalized:
        return 'instagram'
    if 'facebook' in normalized:
        return 'facebook marketplace'
    return 'html'


def create_post(product_id, template_id, caption):
    product = db.get_product_by_id(product_id)
    template = db.get_template_by_id(template_id)
    if not product or not template:
        return None

    content = te.render_with_template(product_id, template_id)
    if content is None:
        return None

    export_format = _normalize_format(template['platform'] or template['name'])
    post_id = db.save_generated_post(
        product_id=product_id,
        template_id=template_id,
        post_type=template['post_type'],
        content=content,
        caption=caption or '',
        export_format=export_format,
    )

    return db.get_post_by_id(post_id)


def update_post(post_id, caption, content, template_id=None):
    current = db.get_post_by_id(post_id)
    if not current:
        return None

    update_kwargs = {
        'content': content,
        'caption': caption,
    }

    if template_id is not None and template_id != current['template_id']:
        template = db.get_template_by_id(template_id)
        if template:
            update_kwargs['template_id'] = template_id
            update_kwargs['export_format'] = _normalize_format(template['platform'] or template['name'])
            update_kwargs['post_type'] = template['post_type']

    db.update_post_content(post_id, **update_kwargs)
    return db.get_post_by_id(post_id)


def get_post_with_product(post_id):
    return db.get_post_by_id(post_id)


def generate_export_html(post_id):
    post = db.get_post_by_id(post_id)
    if not post:
        return None

    style_key = _normalize_format(post['export_format'])
    style_config = STYLE_TEMPLATES.get(style_key, STYLE_TEMPLATES['html'])
    caption_text = html.escape(post['caption'] or '')
    content_text = html.escape(post['content'] or '').replace('\n', '<br>')

    env = Environment(loader=BaseLoader())
    template = env.from_string(EXPORT_HTML_TEMPLATE)
    return template.render(
        title=style_config['title'],
        background=style_config['background'],
        card=style_config['card'],
        text=style_config['text'],
        accent=style_config['accent'],
        product_name=post['product_name'] or 'Product',
        template_name=post['template_name'],
        caption=caption_text,
        content=content_text,
        created_at=post['created_at'],
        export_format_display=style_key.title(),
        caption_label=style_config['caption_label'],
        label=post['post_type'] or 'Marketing Post',
    )
