# Automerce

A Flask-based e-commerce automation platform that manages products, generates promotional posts, and tracks analytics using rule-based automation.

## Features

- **Product Management**: Add, edit, and delete products with categories and featured status
- **Automation Engine**: Triggers promotional post generation based on product changes:
  - R01: New product arrivals
  - R02: Price drops
  - R03: Out of stock alerts
  - R04: Back in stock notifications
  - R05: Featured item promotions
- **Template System**: Customizable post templates for different platforms (WhatsApp, Instagram, Facebook)
- **CSV Import**: Bulk product import with automatic category resolution
- **Analytics Dashboard**: Track product views, interactions, and performance metrics
- **User Authentication**: Secure login with session management
- **Image Upload**: Support for product images (PNG, JPG, JPEG, GIF, WebP)

## Tech Stack

- **Backend**: Flask 2.3.3
- **Database**: SQLite
- **Frontend**: Bootstrap 5, Chart.js
- **Language**: Python 3.14+

## Installation

### Prerequisites
- Python 3.11+
- pip

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/reqless911/Automerce.git
   cd Automerce
   ```

2. Create a virtual environment (optional):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   source .venv/bin/activate  # On macOS/Linux
   ```

3. Install dependencies:
   ```bash
   pip install -r requirement.txt
   ```

4. Set a secret key in your environment before running the app:
   ```bash
   set AUTOMERCE_SECRET_KEY=your-secret-key  # Windows
   export AUTOMERCE_SECRET_KEY=your-secret-key  # macOS/Linux
   ```

5. Run the application:
   ```bash
   python app.py
   ```

   The app will be available at: `http://127.0.0.1:5000`

## Default Login

- **Username**: `admin`
- **Password**: `admin123`

## Project Structure

```
automerce/
├── app.py                      # Main Flask application
├── database.py                 # Database initialization and helpers
├── automation.py               # Rule-based automation engine
├── templates_engine.py         # Post template rendering
├── requirement.txt             # Python dependencies
├── static/
│   ├── css/style.css          # Custom stylesheets
│   └── js/charts.js           # Analytics chart initialization
├── templates/                  # Jinja2 HTML templates
│   ├── base.html              # Base template layout
│   ├── login.html             # Login page
│   ├── dashboard.html         # Dashboard overview
│   ├── products.html          # Products list
│   ├── add_products.html      # Product creation form
│   ├── edit_product.html      # Product editor
│   ├── posts.html             # Generated posts review
│   ├── templates.html         # Post templates manager
│   ├── analytics.html         # Analytics dashboard
│   ├── logs.html              # System logs
│   └── import_csv.html        # CSV bulk import
└── uploads/                    # User-uploaded product images
```

## Database Schema

- **users**: Admin credentials
- **products**: Product inventory with pricing and categories
- **categories**: Product categories
- **templates**: Post templates for different platforms and types
- **generated_posts**: AI-generated promotional posts pending approval
- **analytics_events**: User interaction tracking (views, interactions)
- **system_logs**: Automation trigger events
- **price_history**: Price change tracking

## Automation Rules

### R01 — New Arrival
Triggered when a new product is added. Generates a promotional post using the "New Arrival" template.

### R02 — Price Drop
Triggered when a product's price decreases. Generates a "Price Drop" promotional post.

### R03 — Out of Stock
Triggered when product stock reaches zero. Generates an "Out of Stock" notification.

### R04 — Back in Stock
Triggered when a product is replenished from zero stock. Generates a "Back in Stock" alert.

### R05 — Featured Item
Triggered when a product is marked as featured. Generates a featured item promotional post.

## API Routes

- `GET /` — Login page
- `POST /login` — Authenticate user
- `GET /logout` — Clear session
- `GET /dashboard` — Dashboard overview
- `GET /products` — Product list
- `GET /products/add` — Add product form
- `POST /products/add` — Create product
- `GET /products/edit/<id>` — Edit product form
- `POST /products/edit/<id>` — Update product
- `POST /products/delete/<id>` — Delete product
- `GET /posts` — Review generated posts
- `POST /posts/approve/<id>` — Approve a post
- `GET /templates` — Manage post templates
- `POST /templates/add` — Create template
- `GET /analytics` — View analytics dashboard
- `POST /import-csv` — Bulk import products
- `GET /logs` — System logs

## Development

To run in development mode with auto-reload:

```bash
python app.py
```

The server runs on `http://0.0.0.0:5000` in debug mode.

## License

This project is open source and available under the MIT License.
