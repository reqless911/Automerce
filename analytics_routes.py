import json
from flask import Blueprint, render_template

import database as db
from auth_helpers import login_required

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/dashboard')
@login_required
def dashboard():
    stats = db.get_dashboard_stats()
    design_stats = db.get_design_engine_stats()
    recent_posts = db.get_all_posts()[:5]
    recent_logs = db.get_all_logs()[:5]
    return render_template(
        'dashboard.html',
        stats=stats,
        design_stats=design_stats,
        recent_posts=recent_posts,
        recent_logs=recent_logs,
    )


@analytics_bp.route('/analytics')
@login_required
def analytics():
    top_products = db.get_top_products_by_views(limit=10)
    summary = db.get_product_analytics_summary()
    cat_dist = db.get_category_distribution()
    total_views = db.get_total_views()
    total_interact = db.get_total_interactions()
    total_products = len(db.get_all_products())
    total_posts = db.get_total_posts_count()

    labelled = []
    interaction_values = [r['interactions'] for r in summary]
    max_interactions = max(interaction_values, default=0)

    for i, row in enumerate(summary):
        views = row['views']
        interactions = row['interactions']

        if i == 0 and views > 0:
            label = ('🔥 Trending', 'trending')
        elif interactions == max_interactions and interactions > 0:
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
            'product_id': row['product_id'],
            'name': row['name'],
            'category': row['category_name'] or '—',
            'views': views,
            'interactions': interactions,
            'label_text': label[0],
            'label_class': label[1],
        })

    chart_labels = [r['name'] for r in top_products]
    chart_views = [r['view_count'] for r in top_products]
    donut_labels = [r['category_name'] for r in cat_dist]
    donut_data = [r['product_count'] for r in cat_dist]

    return render_template(
        'analytics.html',
        labelled=labelled,
        chart_labels=json.dumps(chart_labels),
        chart_views=json.dumps(chart_views),
        donut_labels=json.dumps(donut_labels),
        donut_data=json.dumps(donut_data),
        total_views=total_views,
        total_interact=total_interact,
        total_products=total_products,
        total_posts=total_posts,
    )


@analytics_bp.route('/logs')
@login_required
def logs():
    all_logs = db.get_all_logs()
    return render_template('logs.html', logs=all_logs)
