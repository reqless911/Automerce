"""
templates_engine.py — Automerce
Retrieves product data and the appropriate Jinja2 template from the
database, renders the promotional post content, and returns the result.
"""

from jinja2 import Environment, BaseLoader
import database as db


def render_post_content(product_id, post_type):
    """
    Render a promotional post for the given product and post type.

    Looks up the product and the first template whose post_type matches,
    merges the product variables into the template string using Jinja2,
    and returns the rendered text together with the template_id used.

    Returns
    -------
    (content : str | None, template_id : int | None)
    """
    product = db.get_product_by_id(product_id)
    template_row = db.get_template_for_post_type(post_type)

    if not product or not template_row:
        return None, None

    env = Environment(loader=BaseLoader())
    template = env.from_string(template_row['template_body'])

    content = template.render(
        product_name=product['name'],
        price='{:,.0f}'.format(product['price']),
        description=product['description'] or '',
        category=product['category_name'] or '',
        stock=product['stock_quantity'],
    )

    return content, template_row['template_id']


def render_with_template(product_id, template_id):
    """
    Render a post using a specific template (used when admin selects a
    different template from the review queue).

    Returns rendered content string or None.
    """
    product = db.get_product_by_id(product_id)
    template_row = db.get_template_by_id(template_id)

    if not product or not template_row:
        return None

    env = Environment(loader=BaseLoader())
    template = env.from_string(template_row['template_body'])

    return template.render(
        product_name=product['name'],
        price='{:,.0f}'.format(product['price']),
        description=product['description'] or '',
        category=product['category_name'] or '',
        stock=product['stock_quantity'],
    )