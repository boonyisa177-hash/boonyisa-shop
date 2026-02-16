from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'shop.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'dev-secret-key-change-me'

db = SQLAlchemy(app)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500))


def seed_products():
    with app.app_context():
        if Product.query.first():
            print('Sample products already exist. Skipping seeding.')
            return
        samples = [
            Product(name='Gaming Laptop', price=45900.0, image_url='https://images.unsplash.com/photo-1551028719-00167b16ebc5?auto=format&fit=crop&w=600&q=85'),
            Product(name='Mechanical Keyboard', price=3490.0, image_url='https://images.unsplash.com/photo-1587829191301-755e2b8b5e91?auto=format&fit=crop&w=600&q=85'),
            Product(name='Wireless Mouse', price=1290.0, image_url='https://images.unsplash.com/photo-1587829191301-755e2b8b5e91?auto=format&fit=crop&w=600&q=85'),
            Product(name='NVMe SSD 1TB', price=4590.0, image_url='https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?auto=format&fit=crop&w=600&q=85'),
        ]
        db.session.add_all(samples)
        db.session.commit()
        print(f'Inserted {len(samples)} sample products.')


@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == '1234':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))


@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('login'))
    products = Product.query.all()
    return render_template('admin.html', products=products)


@app.route('/admin/add', methods=['POST'])
def admin_add():
    if not session.get('admin'):
        return redirect(url_for('login'))
    name = request.form.get('name')
    price = request.form.get('price')
    image_url = request.form.get('image_url')
    try:
        price_val = float(price)
    except Exception:
        price_val = 0.0
    p = Product(name=name or 'Unnamed', price=price_val, image_url=image_url or '')
    db.session.add(p)
    db.session.commit()
    flash('Product added', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete/<int:product_id>', methods=['POST'])
def admin_delete(product_id):
    if not session.get('admin'):
        return redirect(url_for('login'))
    p = Product.query.get_or_404(product_id)
    db.session.delete(p)
    db.session.commit()
    flash('Product deleted', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []
    product = Product.query.get_or_404(product_id)
    # Check if already in cart, if so increment quantity
    for item in session['cart']:
        if item['id'] == product_id:
            item['qty'] += 1
            session.modified = True
            flash(f'{product.name} added (qty: {item["qty"]})', 'info')
            return redirect(request.referrer or url_for('index'))
    # Add new item to cart
    session['cart'].append({'id': product_id, 'name': product.name, 'price': product.price, 'image_url': product.image_url, 'qty': 1})
    session.modified = True
    flash(f'{product.name} added to cart', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/cart')
def view_cart():
    cart_items = []
    if 'cart' in session:
        for item in session['cart']:
            product = Product.query.get(item['id'])
            if product:
                cart_items.append({'product': product, 'qty': item['qty']})
    total = sum(item['product'].price * item['qty'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)


@app.route('/remove-from-cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['id'] != product_id]
        session.modified = True
        flash('Item removed from cart', 'info')
    return redirect(url_for('view_cart'))


@app.route('/update-cart/<int:product_id>/<action>', methods=['POST'])
def update_cart(product_id, action):
    if 'cart' in session:
        for item in session['cart']:
            if item['id'] == product_id:
                if action == 'increase':
                    item['qty'] += 1
                elif action == 'decrease':
                    if item['qty'] > 1:
                        item['qty'] -= 1
                    else:
                        session['cart'] = [i for i in session['cart'] if i['id'] != product_id]
                session.modified = True
                break
    return redirect(url_for('view_cart'))


if __name__ == '__main__':
    # Ensure DB creation and seeding run inside the Flask application context
    with app.app_context():
        db.create_all()
        seed_products()
        db_path = os.path.join(basedir, 'shop.db')
        print('Database file created (or already exists):', db_path)

    # Start the Flask development server so you can visit the site
    app.run(debug=True)
