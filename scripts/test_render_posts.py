from app import app

with app.test_request_context('/posts'):
    sample_posts = [
        {
            'post_id': 1,
            'product_name': 'Sample Product',
            'post_type': 'New Arrival',
            'template_name': 'WhatsApp — New Arrival',
            'status': 'Approved',
            'created_at': '2026-06-07 00:00:00',
            'content': 'This is a sample post.\nOrder now! "Special"'
        }
    ]
    rendered = app.jinja_env.get_template('posts.html').render(posts=sample_posts)
    if 'data-content=' in rendered:
        print('RENDER_OK')
        start = rendered.find('data-content=')
        print(rendered[start:start+200])
    else:
        print('RENDER_FAIL')
