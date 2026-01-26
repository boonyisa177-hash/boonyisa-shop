from flask import Flask, render_template, request, session, redirect, url_for
import os
from PIL import Image, ImageDraw, ImageFont
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Product data
products = [
    {"id": 1, "name": "Laptop", "price": 1000, "category": "Computer", "image": "laptop.jpg"},
    {"id": 2, "name": "Mouse", "price": 50, "category": "Computer", "image": "mouse.jpg"},
    {"id": 3, "name": "Keyboard", "price": 80, "category": "Computer", "image": "keyboard.jpg"},
    {"id": 4, "name": "Camera", "price": 500, "category": "Camera", "image": "camera.jpg"},
    {"id": 5, "name": "Lens", "price": 300, "category": "Camera", "image": "lens.jpg"},
    {"id": 6, "name": "Tripod", "price": 100, "category": "Camera", "image": "tripod.jpg"},
]

def generate_product_images():
    if not os.path.exists('static/images'):
        os.makedirs('static/images')
    
    for product in products:
        img_path = f'static/images/{product["image"]}'
        if not os.path.exists(img_path):
            # Generate a colorful image with product name
            img = Image.new('RGB', (300, 300), color=(random.randint(100,255), random.randint(100,255), random.randint(100,255)))
            draw = ImageDraw.Draw(img)
            
            # Try to use a font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", 30)
            except:
                font = ImageFont.load_default()
            
            # Center the text
            bbox = draw.textbbox((0, 0), product["name"], font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (300 - text_width) / 2
            y = (300 - text_height) / 2
            draw.text((x, y), product["name"], fill="white", font=font)
            
            img.save(img_path)

@app.route('/')
def home():
    category = request.args.get('category', 'all')
    if category == 'all':
        filtered_products = products
    else:
        filtered_products = [p for p in products if p['category'] == category]
    
    cart_count = sum(session.get('cart', {}).values())
    return render_template('index.html', products=filtered_products, cart_count=cart_count, selected_category=category)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = {}
    if str(product_id) in session['cart']:
        session['cart'][str(product_id)] += 1
    else:
        session['cart'][str(product_id)] = 1
    return redirect(url_for('home'))

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    if 'cart' in session and str(product_id) in session['cart']:
        if session['cart'][str(product_id)] > 1:
            session['cart'][str(product_id)] -= 1
        else:
            del session['cart'][str(product_id)]
    return redirect(url_for('home'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        # In a real app, process payment here
        session.pop('cart', None)
        return redirect(url_for('home'))
    
    cart_items = []
    total = 0
    if 'cart' in session:
        for pid, qty in session['cart'].items():
            product = next((p for p in products if p['id'] == int(pid)), None)
            if product:
                cart_items.append({'product': product, 'quantity': qty, 'subtotal': product['price'] * qty})
                total += product['price'] * qty
    
    return render_template('checkout.html', cart_items=cart_items, total=total)

if __name__ == '__main__':
    generate_product_images()
    app.run(debug=True)