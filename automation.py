"""
automation.py — Automerce
Rule-based automation engine. Evaluates product change events against
the five defined rules (R01–R05) and triggers post generation.

Rules:
    R01  New product added            → New Arrival post
    R02  Price decreased              → Price Drop post
    R03  Stock quantity reaches 0     → Out of Stock post
    R04  Stock replenished from 0     → Back in Stock post
    R05  Product marked as featured   → Featured Item post
"""

import database as db
import templates_engine as te


def detect_and_generate(product_id, change_type, old_data=None, new_data=None):
    """
    Evaluate the product change event against automation rules R01–R05.
    Generate and persist a promotional post for each triggered rule.

    Parameters
    ----------
    product_id  : int   — ID of the affected product
    change_type : str   — One of: 'new_product', 'price_update',
                          'stock_update', 'featured'
    old_data    : dict  — Previous product values (price, stock). May be None
                          for new products.
    new_data    : dict  — Updated product values (price, stock, is_featured).
    """

    if old_data is None:
        old_data = {}
    if new_data is None:
        new_data = {}

    post_type = None

    # ------------------------------------------------------------------
    # R01 — New product added to inventory
    # ------------------------------------------------------------------
    if change_type == 'new_product':
        post_type = 'New Arrival'

    # ------------------------------------------------------------------
    # R02 — Price decreased (also records price history)
    # ------------------------------------------------------------------
    elif change_type == 'price_update':
        old_price = old_data.get('price')
        new_price = new_data.get('price')

        if old_price is not None and new_price is not None:
            db.record_price_history(product_id, old_price, new_price)
            if float(new_price) < float(old_price):
                post_type = 'Price Drop'

    # ------------------------------------------------------------------
    # R03 — Stock reaches zero  |  R04 — Stock replenished from zero
    # ------------------------------------------------------------------
    elif change_type == 'stock_update':
        old_stock = old_data.get('stock', 1)
        new_stock = new_data.get('stock', 1)

        if int(new_stock) == 0 and int(old_stock) > 0:
            # R03
            post_type = 'Out of Stock'
        elif int(new_stock) > 0 and int(old_stock) == 0:
            # R04
            post_type = 'Back in Stock'

    # ------------------------------------------------------------------
    # R05 — Product marked as featured
    # ------------------------------------------------------------------
    elif change_type == 'featured':
        if new_data.get('is_featured', 0):
            post_type = 'Featured Item'

    # ------------------------------------------------------------------
    # Generate, save, and log the post if a rule was triggered
    # ------------------------------------------------------------------
    if post_type:
        content, template_id = te.render_post_content(product_id, post_type)

        if content:
            post_id = db.save_generated_post(product_id, post_type, content, template_id)
            db.log_action(post_id, f'Generated {post_type} post', post_type)

    return post_type  # Caller may use this for flash messages


def run_on_edit(product_id, old_price, old_stock, new_price, new_stock,
                old_featured, new_featured):
    """
    Convenience wrapper called by the edit-product route.
    Checks price, stock, and featured status in one call and fires
    the appropriate rules. Returns a list of triggered post types.
    """
    triggered = []

    # Price change
    if float(new_price) != float(old_price):
        result = detect_and_generate(
            product_id,
            'price_update',
            old_data={'price': old_price},
            new_data={'price': new_price}
        )
        if result:
            triggered.append(result)

    # Stock change
    if int(new_stock) != int(old_stock):
        result = detect_and_generate(
            product_id,
            'stock_update',
            old_data={'stock': old_stock},
            new_data={'stock': new_stock}
        )
        if result:
            triggered.append(result)

    # Featured status change (newly marked as featured)
    if int(new_featured) == 1 and int(old_featured) == 0:
        result = detect_and_generate(
            product_id,
            'featured',
            old_data={'is_featured': old_featured},
            new_data={'is_featured': new_featured}
        )
        if result:
            triggered.append(result)

    return triggered