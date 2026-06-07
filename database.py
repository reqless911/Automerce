"""
database.py — Automerce
Handles database initialisation, schema creation, seed data, and all
data-access helper functions used by app.py and automation.py.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'automerce.db')


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_db():
    """Return a sqlite3 connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

def init_db():
    """Create all tables if they do not already exist, then seed defaults."""
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            product_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT    NOT NULL,
            price          REAL    NOT NULL,
            stock_quantity INTEGER DEFAULT 0,
            description    TEXT,
            image_path     TEXT,
            is_featured    INTEGER DEFAULT 0,
            category_id    INTEGER REFERENCES categories(category_id),
            created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS price_history (
            history_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  INTEGER NOT NULL REFERENCES products(product_id),
            old_price   REAL,
            new_price   REAL,
            changed_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS templates (
            template_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            platform      TEXT,
            template_body TEXT,
            post_type     TEXT,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS generated_posts (
            post_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id   INTEGER REFERENCES products(product_id),
            template_id  INTEGER REFERENCES templates(template_id),
            post_type    TEXT,
            caption      TEXT,
            content      TEXT,
            export_format TEXT DEFAULT 'html',
            status       TEXT    DEFAULT 'Pending',
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at   DATETIME
        );

        CREATE TABLE IF NOT EXISTS analytics_events (
            event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  INTEGER REFERENCES products(product_id),
            event_type  TEXT,
            occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS system_logs (
            log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id       INTEGER REFERENCES generated_posts(post_id),
            action        TEXT,
            trigger_event TEXT,
            logged_at     DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE,
            password_hash TEXT,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    _ensure_generated_posts_columns(conn)
    conn.commit()
    conn.close()
    _seed_defaults()


def _ensure_generated_posts_columns(conn):
    columns = {row['name'] for row in conn.execute("PRAGMA table_info(generated_posts)").fetchall()}
    if 'caption' not in columns:
        conn.execute("ALTER TABLE generated_posts ADD COLUMN caption TEXT")
    if 'export_format' not in columns:
        conn.execute("ALTER TABLE generated_posts ADD COLUMN export_format TEXT DEFAULT 'html'")
    if 'updated_at' not in columns:
        conn.execute("ALTER TABLE generated_posts ADD COLUMN updated_at DATETIME")


# ---------------------------------------------------------------------------
# Seed default data
# ---------------------------------------------------------------------------

def _seed_defaults():
    """Insert default admin user, categories, and post templates if absent."""
    conn = get_db()
    c = conn.cursor()

    # Default admin user
    existing = c.execute("SELECT 1 FROM users WHERE username = 'admin'").fetchone()
    if not existing:
        c.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ('admin', generate_password_hash('admin123'))
        )

    # Default categories
    for cat in ('Clothing', 'Accessories', 'Household'):
        exists = c.execute("SELECT 1 FROM categories WHERE name = ?", (cat,)).fetchone()
        if not exists:
            c.execute("INSERT INTO categories (name) VALUES (?)", (cat,))

    # Default post templates (5 as specified in the project paper)
    default_templates = [
        (
            'WhatsApp — New Arrival',
            'WhatsApp',
            '🎉 *NEW ARRIVAL* 🎉\n\n'
            '👕 *{{ product_name }}*\n\n'
            '🎀 {{ description }}\n\n'
            '💰 Price: *KES {{ price }}*\n'
            '📦 Category: {{ category }} | In stock ✅\n\n'
            '📩 Order now via DM or call us\n'
            '🚚 Delivery available in Mombasa\n'
            '📍 Nawal Centre, Mombasa\n\n'
            '#NawalCentre #NewArrival #MombasaShopping',
            'New Arrival'
        ),
        (
            'Instagram — New Arrival',
            'Instagram',
            '✨ NEW IN ✨\n\n'
            '{{ product_name }}\n\n'
            '{{ description }}\n\n'
            '💵 KES {{ price }}\n\n'
            '#NawalCentre #NewArrival #{{ category }} #MombasaFashion #ShopNow',
            'New Arrival'
        ),
        (
            'Facebook Marketplace — New Arrival',
            'Facebook Marketplace',
            '🛍️ {{ product_name }}\n\n'
            'Price: KES {{ price }}\n'
            'Condition: New\n'
            'Category: {{ category }}\n\n'
            '{{ description }}\n\n'
            '📞 Contact us to order.\n'
            '🚚 Delivery available in Mombasa.\n'
            '📍 Nawal Centre, Mombasa.',
            'New Arrival'
        ),
        (
            'WhatsApp — Price Drop',
            'WhatsApp',
            '🔥 *PRICE DROP ALERT* 🔥\n\n'
            '👕 *{{ product_name }}*\n\n'
            '💸 New Price: *KES {{ price }}*\n'
            '📦 Category: {{ category }}\n\n'
            '{{ description }}\n\n'
            '📩 Order now via DM or call us\n'
            '🚚 Delivery available in Mombasa\n'
            '📍 Nawal Centre, Mombasa\n\n'
            '#NawalCentre #PriceDrop #Deals #MombasaShopping',
            'Price Drop'
        ),
        (
            'WhatsApp — Out of Stock',
            'WhatsApp',
            '😔 *OUT OF STOCK*\n\n'
            '👕 *{{ product_name }}*\n\n'
            'This item is currently sold out.\n\n'
            '📩 DM us to be notified when it is back in stock.\n'
            '📍 Nawal Centre, Mombasa\n\n'
            '#NawalCentre #SoldOut #ComingSoon',
            'Out of Stock'
        ),
    ]

    for name, platform, body, post_type in default_templates:
        exists = c.execute(
            "SELECT 1 FROM templates WHERE name = ?", (name,)
        ).fetchone()
        if not exists:
            c.execute(
                "INSERT INTO templates (name, platform, template_body, post_type) VALUES (?,?,?,?)",
                (name, platform, body, post_type)
            )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def get_user_by_username(username):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return user


# ---------------------------------------------------------------------------
# Category helpers
# ---------------------------------------------------------------------------

def get_all_categories():
    conn = get_db()
    rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return rows


def add_category(name):
    conn = get_db()
    conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Product helpers
# ---------------------------------------------------------------------------

def get_all_products():
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.category_id
        ORDER BY p.created_at DESC
    """).fetchall()
    conn.close()
    return rows


def get_product_by_id(product_id):
    conn = get_db()
    row = conn.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.category_id
        WHERE p.product_id = ?
    """, (product_id,)).fetchone()
    conn.close()
    return row


def add_product(name, price, stock_quantity, description, image_path, category_id, is_featured=0):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO products (name, price, stock_quantity, description, image_path, category_id, is_featured)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, price, stock_quantity, description, image_path, category_id, is_featured))
    product_id = c.lastrowid
    conn.commit()
    conn.close()
    return product_id


def update_product(product_id, name, price, stock_quantity, description, image_path, category_id, is_featured=0):
    """Update product and return (old_price, old_stock) for automation engine."""
    conn = get_db()
    old = conn.execute(
        "SELECT price, stock_quantity FROM products WHERE product_id = ?", (product_id,)
    ).fetchone()
    old_price = old['price'] if old else None
    old_stock = old['stock_quantity'] if old else None

    conn.execute("""
        UPDATE products
        SET name=?, price=?, stock_quantity=?, description=?, image_path=?,
            category_id=?, is_featured=?
        WHERE product_id=?
    """, (name, price, stock_quantity, description, image_path, category_id, is_featured, product_id))
    conn.commit()
    conn.close()
    return old_price, old_stock


def delete_product(product_id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()


def get_out_of_stock_count():
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM products WHERE stock_quantity = 0"
    ).fetchone()
    conn.close()
    return row['cnt']


# ---------------------------------------------------------------------------
# Price history helpers
# ---------------------------------------------------------------------------

def record_price_history(product_id, old_price, new_price):
    conn = get_db()
    conn.execute("""
        INSERT INTO price_history (product_id, old_price, new_price)
        VALUES (?, ?, ?)
    """, (product_id, old_price, new_price))
    conn.commit()
    conn.close()


def get_price_history(product_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM price_history WHERE product_id = ?
        ORDER BY changed_at DESC
    """, (product_id,)).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

def get_all_templates():
    conn = get_db()
    rows = conn.execute("SELECT * FROM templates ORDER BY platform, post_type").fetchall()
    conn.close()
    return rows


def get_template_by_id(template_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM templates WHERE template_id = ?", (template_id,)
    ).fetchone()
    conn.close()
    return row


def get_template_for_post_type(post_type):
    """Return the first matching template for a given post type."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM templates WHERE post_type = ? LIMIT 1", (post_type,)
    ).fetchone()
    conn.close()
    return row


def add_template(name, platform, template_body, post_type):
    conn = get_db()
    conn.execute("""
        INSERT INTO templates (name, platform, template_body, post_type)
        VALUES (?, ?, ?, ?)
    """, (name, platform, template_body, post_type))
    conn.commit()
    conn.close()


def update_template(template_id, name, platform, template_body, post_type):
    conn = get_db()
    conn.execute("""
        UPDATE templates SET name=?, platform=?, template_body=?, post_type=?
        WHERE template_id=?
    """, (name, platform, template_body, post_type, template_id))
    conn.commit()
    conn.close()


def delete_template(template_id):
    conn = get_db()
    conn.execute("DELETE FROM templates WHERE template_id = ?", (template_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Generated posts helpers
# ---------------------------------------------------------------------------

def save_generated_post(product_id, post_type, content, template_id=None, caption=None, export_format='html'):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO generated_posts (
            product_id,
            template_id,
            post_type,
            caption,
            content,
            export_format,
            status,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'Pending', CURRENT_TIMESTAMP)
    """, (product_id, template_id, post_type, caption, content, export_format))
    post_id = c.lastrowid
    conn.commit()
    conn.close()
    return post_id


def get_all_posts():
    conn = get_db()
    rows = conn.execute("""
        SELECT gp.*, p.name AS product_name, t.name AS template_name
        FROM generated_posts gp
        LEFT JOIN products p ON gp.product_id = p.product_id
        LEFT JOIN templates t ON gp.template_id = t.template_id
        ORDER BY gp.created_at DESC
    """).fetchall()
    conn.close()
    return rows


def get_pending_posts():
    conn = get_db()
    rows = conn.execute("""
        SELECT gp.*, p.name AS product_name, t.name AS template_name
        FROM generated_posts gp
        LEFT JOIN products p ON gp.product_id = p.product_id
        LEFT JOIN templates t ON gp.template_id = t.template_id
        WHERE gp.status = 'Pending'
        ORDER BY gp.created_at DESC
    """).fetchall()
    conn.close()
    return rows


def get_post_by_id(post_id):
    conn = get_db()
    row = conn.execute("""
        SELECT gp.*, p.name AS product_name, t.name AS template_name
        FROM generated_posts gp
        LEFT JOIN products p ON gp.product_id = p.product_id
        LEFT JOIN templates t ON gp.template_id = t.template_id
        WHERE gp.post_id = ?
    """, (post_id,)).fetchone()
    conn.close()
    return row


def update_post_content(post_id, content, caption=None, template_id=None, export_format=None, post_type=None):
    conn = get_db()
    fields = ["content = ?", "updated_at = CURRENT_TIMESTAMP"]
    params = [content]

    if caption is not None:
        fields.append("caption = ?")
        params.append(caption)
    if template_id is not None:
        fields.append("template_id = ?")
        params.append(template_id)
    if export_format is not None:
        fields.append("export_format = ?")
        params.append(export_format)
    if post_type is not None:
        fields.append("post_type = ?")
        params.append(post_type)

    query = f"UPDATE generated_posts SET {', '.join(fields)} WHERE post_id = ?"
    params.append(post_id)
    conn.execute(query, tuple(params))
    conn.commit()
    conn.close()


def approve_post(post_id):
    conn = get_db()
    conn.execute("UPDATE generated_posts SET status='Approved' WHERE post_id=?", (post_id,))
    conn.commit()
    conn.close()


def get_pending_post_count():
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM generated_posts WHERE status = 'Pending'"
    ).fetchone()
    conn.close()
    return row['cnt']


def get_total_posts_count():
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) AS cnt FROM generated_posts").fetchone()
    conn.close()
    return row['cnt']


# ---------------------------------------------------------------------------
# Analytics helpers
# ---------------------------------------------------------------------------

def log_analytics_event(product_id, event_type):
    conn = get_db()
    conn.execute("""
        INSERT INTO analytics_events (product_id, event_type)
        VALUES (?, ?)
    """, (product_id, event_type))
    conn.commit()
    conn.close()


def get_top_products_by_views(limit=10):
    """Return products ordered by view event count (last 7 days)."""
    since = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db()
    rows = conn.execute("""
        SELECT p.product_id, p.name,
               COUNT(ae.event_id) AS view_count
        FROM products p
        LEFT JOIN analytics_events ae
            ON p.product_id = ae.product_id
            AND ae.event_type = 'view'
            AND ae.occurred_at >= ?
        GROUP BY p.product_id
        ORDER BY view_count DESC
        LIMIT ?
    """, (since, limit)).fetchall()
    conn.close()
    return rows


def get_product_analytics_summary():
    """Return per-product view and interaction counts for the performance table."""
    conn = get_db()
    rows = conn.execute("""
        SELECT p.product_id, p.name,
               c.name AS category_name,
               COALESCE(SUM(CASE WHEN ae.event_type = 'view' THEN 1 ELSE 0 END), 0) AS views,
               COALESCE(SUM(CASE WHEN ae.event_type = 'interaction' THEN 1 ELSE 0 END), 0) AS interactions
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.category_id
        LEFT JOIN analytics_events ae ON p.product_id = ae.product_id
        GROUP BY p.product_id
        ORDER BY views DESC
    """).fetchall()
    conn.close()
    return rows


def get_category_distribution():
    """Return product count per category for the donut chart."""
    conn = get_db()
    rows = conn.execute("""
        SELECT c.name AS category_name, COUNT(p.product_id) AS product_count
        FROM categories c
        LEFT JOIN products p ON c.category_id = p.category_id
        GROUP BY c.category_id
        ORDER BY product_count DESC
    """).fetchall()
    conn.close()
    return rows


def get_total_views():
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM analytics_events WHERE event_type = 'view'"
    ).fetchone()
    conn.close()
    return row['cnt']


def get_total_interactions():
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM analytics_events WHERE event_type = 'interaction'"
    ).fetchone()
    conn.close()
    return row['cnt']


# ---------------------------------------------------------------------------
# System log helpers
# ---------------------------------------------------------------------------

def log_action(post_id, action, trigger_event):
    conn = get_db()
    conn.execute("""
        INSERT INTO system_logs (post_id, action, trigger_event)
        VALUES (?, ?, ?)
    """, (post_id, action, trigger_event))
    conn.commit()
    conn.close()


def get_all_logs():
    conn = get_db()
    rows = conn.execute("""
        SELECT sl.*, p.name AS product_name
        FROM system_logs sl
        LEFT JOIN generated_posts gp ON sl.post_id = gp.post_id
        LEFT JOIN products p ON gp.product_id = p.product_id
        ORDER BY sl.logged_at DESC
    """).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Dashboard stats helper
# ---------------------------------------------------------------------------

def get_dashboard_stats():
    conn = get_db()
    total_products = conn.execute("SELECT COUNT(*) AS cnt FROM products").fetchone()['cnt']
    total_posts = conn.execute("SELECT COUNT(*) AS cnt FROM generated_posts").fetchone()['cnt']
    pending_posts = conn.execute(
        "SELECT COUNT(*) AS cnt FROM generated_posts WHERE status = 'Pending'"
    ).fetchone()['cnt']
    out_of_stock = conn.execute(
        "SELECT COUNT(*) AS cnt FROM products WHERE stock_quantity = 0"
    ).fetchone()['cnt']
    conn.close()
    return {
        'total_products': total_products,
        'total_posts': total_posts,
        'pending_posts': pending_posts,
        'out_of_stock': out_of_stock,
    }