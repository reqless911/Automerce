import pandas as pd
import database as db
from validators import validate_csv_row

REQUIRED_COLUMNS = ['product_name', 'category', 'price', 'stock_quantity', 'description']


def normalize_columns(df):
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    return df


def parse_csv_file(file):
    df = pd.read_csv(file)
    df = normalize_columns(df)

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError('CSV is missing required columns: {}'.format(', '.join(missing_columns)))

    valid_rows = []
    errors = []

    for index, row in df.iterrows():
        row_data, row_errors = validate_csv_row(row)
        if row_errors:
            errors.append({'row': index + 1, 'errors': row_errors})
            continue
        valid_rows.append(row_data)

    return valid_rows, errors


def import_products(rows):
    conn = db.get_db()
    cursor = conn.cursor()

    existing_categories = cursor.execute(
        'SELECT name, category_id FROM categories'
    ).fetchall()
    category_cache = {row['name']: row['category_id'] for row in existing_categories}

    new_categories = [row['category'] for row in rows if row['category'] not in category_cache]
    unique_new_categories = list(dict.fromkeys(new_categories))

    if unique_new_categories:
        cursor.executemany(
            'INSERT INTO categories (name) VALUES (?)',
            [(category,) for category in unique_new_categories]
        )
        conn.commit()
        placeholders = ','.join(['?'] * len(unique_new_categories))
        new_rows = cursor.execute(
            f'SELECT name, category_id FROM categories WHERE name IN ({placeholders})',
            unique_new_categories
        ).fetchall()
        category_cache.update({row['name']: row['category_id'] for row in new_rows})

    inserted_ids = []
    for row in rows:
        category_id = category_cache.get(row['category'])
        cursor.execute(
            'INSERT INTO products (name, price, stock_quantity, description, image_path, category_id) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (
                row['product_name'],
                row['price'],
                row['stock_quantity'],
                row['description'],
                None,
                category_id,
            )
        )
        inserted_ids.append(cursor.lastrowid)

    conn.commit()
    conn.close()
    return inserted_ids


def import_csv_products(file):
    rows, errors = parse_csv_file(file)
    inserted_ids = []

    if rows:
        inserted_ids = import_products(rows)

    return inserted_ids, errors
