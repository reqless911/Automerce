import os
from flask import Flask, send_from_directory

import database as db
from auth_routes import auth_bp
from product_routes import products_bp
from post_routes import posts_bp
from analytics_routes import analytics_bp

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('AUTOMERCE_SECRET_KEY', 'automerce-dev-key')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    db.init_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(analytics_bp)

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
