from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'hotel.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'dev-secret-key-change-me'

# File upload configuration
UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create uploads folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# In-memory global reviews (visible to all users). Used alongside session-backed reviews.
REVIEWS = {}

def get_reviews_for(room_id):
    key = str(room_id)
    out = []
    # global stored reviews
    if key in REVIEWS:
        out.extend(REVIEWS.get(key, []))
    # session reviews (per-user)
    try:
        sess = session.get('reviews', {})
        out.extend(sess.get(key, []))
    except Exception:
        pass
    return out

app.jinja_env.globals['get_reviews'] = get_reviews_for

# Seed a demo review for room 1
REVIEWS.setdefault('1', []).append({'name': 'สมชาย', 'rating': 5, 'comment': 'บริการดี ห้องสะอาด และใกล้สถานที่ท่องเที่ยว'})

def format_date(value, outfmt='%d/%m/%Y'):
    from datetime import datetime
    if not value:
        return ''
    # Try common stored format YYYY-MM-DD or pass-through
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            d = datetime.strptime(value, fmt)
            return d.strftime(outfmt)
        except Exception:
            continue
    return value

app.jinja_env.filters['format_date'] = format_date


def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_review_image(file):
    """Save uploaded image and return the filename, or None if invalid"""
    if not file or file.filename == '':
        return None
    
    if not allowed_file(file.filename):
        return None
    
    try:
        # Generate unique filename to avoid collisions
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"review_{uuid.uuid4().hex}_{int(datetime.now().timestamp())}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return filename
    except Exception as e:
        print(f"Error saving file: {e}")
        return None


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    room_type = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    price_per_night = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500))
    amenities = db.Column(db.String(500))


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(200), nullable=False)
    customer_email = db.Column(db.String(200), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    room_name = db.Column(db.String(200), nullable=False)
    room_type = db.Column(db.String(100))
    check_in = db.Column(db.String(20), nullable=False)
    check_out = db.Column(db.String(20), nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    price_per_night = db.Column(db.Float, nullable=False)
    nights = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='completed')  # completed, cancelled, pending
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


def seed_rooms():
    with app.app_context():
        if Room.query.first():
            print('Sample rooms already exist. Skipping seeding.')
            return
        samples = [
            Room(name='Deluxe Room', room_type='Deluxe', capacity=2, price_per_night=2500.0, 
                 image_url='https://images.unsplash.com/photo-1631049307264-da0ec9d70304?auto=format&fit=crop&w=600&q=85',
                 amenities='WiFi, AC, TV, Mini Bar'),
            Room(name='Suite Room', room_type='Suite', capacity=4, price_per_night=4500.0,
                 image_url='https://images.unsplash.com/photo-1582719471384-894fbb16e074?auto=format&fit=crop&w=600&q=85',
                 amenities='WiFi, AC, LCD TV, Jacuzzi, Mini Bar'),
            Room(name='Standard Room', room_type='Standard', capacity=2, price_per_night=1500.0,
                 image_url='https://images.unsplash.com/photo-1578500494198-246f612d03b3?auto=format&fit=crop&w=600&q=85',
                 amenities='WiFi, AC, TV'),
            Room(name='Family Room', room_type='Family', capacity=6, price_per_night=5500.0,
                 image_url='https://images.unsplash.com/photo-1561181286-d3fee7d55364?auto=format&fit=crop&w=600&q=85',
                 amenities='WiFi, AC, 2 TVs, Kitchen'),
        ]
        db.session.add_all(samples)
        db.session.commit()
        print(f'Inserted {len(samples)} sample rooms.')


@app.route('/')
def index():
    rooms = Room.query.all()
    return render_template('index.html', rooms=rooms)


@app.route('/booking/<int:room_id>', methods=['GET', 'POST'])
def booking(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        guests = request.form.get('guests')
        # Normalize incoming date formats to ISO (YYYY-MM-DD).
        from datetime import datetime
        def to_iso(date_str):
            if not date_str:
                return date_str
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    d = datetime.strptime(date_str, fmt)
                    return d.strftime('%Y-%m-%d')
                except Exception:
                    continue
            return date_str

        check_in = to_iso(check_in)
        check_out = to_iso(check_out)
        
        if 'bookings' not in session:
            session['bookings'] = []
        
        session['bookings'].append({
            'room_id': room_id,
            'room_name': room.name,
            'room_type': room.room_type,
            'check_in': check_in,
            'check_out': check_out,
            'guests': guests,
            'price_per_night': room.price_per_night
        })
        session.modified = True
        flash(f'Booking for {room.name} added', 'success')
        return redirect(url_for('view_booking'))
    
    return render_template('booking_form.html', room=room)


@app.route('/review/<int:room_id>', methods=['POST'])
def add_review(room_id):
    name = request.form.get('review_name') or 'Anonymous'
    try:
        rating = int(request.form.get('rating') or 5)
    except Exception:
        rating = 5
    comment = request.form.get('comment') or ''
    
    # Handle image upload
    image_filename = None
    if 'review_image' in request.files:
        file = request.files['review_image']
        if file and file.filename != '':
            image_filename = save_review_image(file)
            if not image_filename:
                flash('ไม่สามารถบันทึกรูปภาพ - โปรดใช้รูปภาพ PNG, JPG, JPEG, GIF หรือ WEBP ที่มีขนาดไม่เกิน 5 MB', 'warning')

    reviews = session.get('reviews', {})
    key = str(room_id)
    lst = reviews.get(key, [])
    review_item = {
        'name': name, 
        'rating': rating, 
        'comment': comment,
        'image': image_filename,
        'date': datetime.now().strftime('%d/%m/%Y %H:%M')
    }
    lst.append(review_item)
    reviews[key] = lst
    session['reviews'] = reviews
    session.modified = True
    flash('ขอบคุณสำหรับรีวิว!', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/my-bookings')
def view_booking():
    # Get current session bookings (pending/temporary)
    session_bookings = session.get('bookings', [])
    total_price = 0
    
    for booking in session_bookings:
        try:
            check_in = datetime.strptime(booking.get('check_in', ''), '%Y-%m-%d')
            check_out = datetime.strptime(booking.get('check_out', ''), '%Y-%m-%d')
            nights = (check_out - check_in).days
            if nights < 1:
                nights = 1
        except Exception:
            nights = booking.get('nights', 1)

        booking['nights'] = nights
        booking['total'] = booking.get('price_per_night', 0) * nights
        total_price += booking['total']
    
    # Get historical bookings from database (only if user has logged in with an email)
    historical_bookings = []
    customer_email = session.get('customer_email')
    if customer_email:
        historical_bookings = Booking.query.filter_by(customer_email=customer_email).order_by(Booking.created_at.desc()).all()

    return render_template('bookings.html', bookings=session_bookings, total_price=total_price, historical_bookings=historical_bookings)


@app.route('/checkout')
def checkout():
    bookings = session.get('bookings', [])
    if not bookings:
        flash('ไม่มีการจองที่ต้องชำระเงิน', 'warning')
        return redirect(url_for('index'))
    
    # Calculate total nights and price
    total_price = 0
    for booking in bookings:
        from datetime import datetime
        check_in = datetime.strptime(booking['check_in'], '%Y-%m-%d')
        check_out = datetime.strptime(booking['check_out'], '%Y-%m-%d')
        nights = (check_out - check_in).days
        if nights < 1:
            nights = 1
        booking['nights'] = nights
        booking['total'] = booking['price_per_night'] * nights
        total_price += booking['total']
    
    return render_template('checkout.html', bookings=bookings, total_price=total_price)


@app.route('/payment', methods=['GET'])
def payment_page():
    bookings = session.get('bookings', [])
    if not bookings:
        flash('ไม่มีการจองที่ต้องชำระเงิน', 'warning')
        return redirect(url_for('index'))

    # Ensure nights and totals are calculated
    from datetime import datetime
    total_price = 0
    for booking in bookings:
        try:
            check_in = datetime.strptime(booking['check_in'], '%Y-%m-%d')
            check_out = datetime.strptime(booking['check_out'], '%Y-%m-%d')
            nights = (check_out - check_in).days
            if nights < 1:
                nights = 1
        except Exception:
            nights = booking.get('nights', 1)

        booking['nights'] = nights
        booking['total'] = booking.get('price_per_night', 0) * nights
        total_price += booking['total']

    return render_template('payment.html', bookings=bookings, total_price=total_price)


@app.route('/payment', methods=['POST'])
def payment():
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    card_number = request.form.get('card_number')
    
    if not all([full_name, email, card_number]):
        flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'danger')
        return redirect(url_for('checkout'))
    
    # Mock payment processing (in real app, integrate with payment gateway)
    bookings = session.get('bookings', [])
    total_price = sum(booking.get('total', 0) for booking in bookings if 'total' in booking)
    
    # Save bookings to database
    for booking in bookings:
        try:
            check_in = datetime.strptime(booking['check_in'], '%Y-%m-%d')
            check_out = datetime.strptime(booking['check_out'], '%Y-%m-%d')
            nights = (check_out - check_in).days
            if nights < 1:
                nights = 1
        except Exception:
            nights = booking.get('nights', 1)
        
        db_booking = Booking(
            customer_name=full_name,
            customer_email=email,
            room_id=booking['room_id'],
            room_name=booking['room_name'],
            room_type=booking.get('room_type', ''),
            check_in=booking['check_in'],
            check_out=booking['check_out'],
            guests=int(booking.get('guests', 1)),
            price_per_night=booking['price_per_night'],
            nights=nights,
            total_price=booking.get('total', 0),
            status='completed'
        )
        db.session.add(db_booking)
    
    db.session.commit()
    
    # Store payment info and customer email in session for future reference
    session['payment_info'] = {
        'full_name': full_name,
        'email': email,
        'total_price': total_price,
        'booking_count': len(bookings),
        'status': 'success'
    }
    session['customer_email'] = email
    session['customer_name'] = full_name
    session.modified = True
    flash('ชำระเงินสำเร็จ', 'success')
    return redirect(url_for('payment_success'))


@app.route('/payment-success')
def payment_success():
    payment_info = session.get('payment_info')
    if not payment_info:
        return redirect(url_for('index'))
    
    bookings = session.get('bookings', [])
    return render_template('payment_success.html', payment_info=payment_info, bookings=bookings)


@app.route('/clear-bookings', methods=['POST'])
def clear_bookings():
    session.pop('bookings', None)
    session.pop('payment_info', None)
    session.modified = True
    flash('การจองและข้อมูลการชำระเงินถูกลบออก', 'info')
    return redirect(url_for('index'))
@app.route('/cancel-booking/<int:booking_index>', methods=['POST'])
def cancel_booking(booking_index):
    if 'bookings' in session:
        if 0 <= booking_index < len(session['bookings']):
            session['bookings'].pop(booking_index)
            session.modified = True
            flash('Booking cancelled', 'info')
    return redirect(url_for('view_booking'))


@app.route('/delete-review-image/<int:room_id>/<int:review_index>', methods=['POST'])
def delete_review_image(room_id, review_index):
    """Delete a review image"""
    reviews = session.get('reviews', {})
    key = str(room_id)
    
    if key in reviews and 0 <= review_index < len(reviews[key]):
        review = reviews[key][review_index]
        # Delete the image file if it exists
        if review.get('image'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], review['image'])
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                print(f"Error deleting file: {e}")
        
        # Remove the image from the review
        review['image'] = None
        session['reviews'] = reviews
        session.modified = True
        flash('ลบรูปภาพสำเร็จ', 'success')
    
    return redirect(request.referrer or url_for('reviews_page'))


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
    rooms = Room.query.all()
    return render_template('admin.html', rooms=rooms)


@app.route('/admin/bookings')
def admin_bookings():
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    # Get all bookings from database
    all_bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    
    # Group by customer email for summary
    customer_summary = {}
    for booking in all_bookings:
        email = booking.customer_email
        if email not in customer_summary:
            customer_summary[email] = {
                'name': booking.customer_name,
                'email': email,
                'count': 0,
                'total_spent': 0
            }
        customer_summary[email]['count'] += 1
        customer_summary[email]['total_spent'] += booking.total_price
    
    return render_template('admin_bookings.html', bookings=all_bookings, customer_summary=customer_summary)


@app.route('/reviews')
def reviews_page():
    # Build mapping room_id -> room object and reviews list
    rooms = Room.query.all()
    rooms_map = {str(r.id): r for r in rooms}
    # collect reviews for all rooms
    all_reviews = {}
    # include global REVIEWS
    for rid, revs in REVIEWS.items():
        all_reviews.setdefault(rid, []).extend(revs)
    # include session reviews
    try:
        sess = session.get('reviews', {})
        for rid, revs in sess.items():
            all_reviews.setdefault(rid, []).extend(revs)
    except Exception:
        pass

    # prepare list of (room, reviews)
    grouped = []
    for rid, revs in all_reviews.items():
        room = rooms_map.get(rid)
        grouped.append({'room': room, 'reviews': revs})

    return render_template('reviews.html', grouped=grouped)


@app.route('/admin/add', methods=['POST'])
def admin_add():
    if not session.get('admin'):
        return redirect(url_for('login'))
    name = request.form.get('name')
    room_type = request.form.get('room_type')
    capacity = request.form.get('capacity')
    price_per_night = request.form.get('price_per_night')
    image_url = request.form.get('image_url')
    amenities = request.form.get('amenities')
    try:
        capacity_val = int(capacity)
        price_val = float(price_per_night)
    except Exception:
        capacity_val = 1
        price_val = 0.0
    room = Room(name=name or 'Unnamed', room_type=room_type or 'Standard', 
                capacity=capacity_val, price_per_night=price_val, 
                image_url=image_url or '', amenities=amenities or '')
    db.session.add(room)
    db.session.commit()
    flash('Room added', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete/<int:room_id>', methods=['POST'])
def admin_delete(room_id):
    if not session.get('admin'):
        return redirect(url_for('login'))
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    flash('Room deleted', 'success')
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    # Ensure DB creation and seeding run inside the Flask application context
    with app.app_context():
        db.create_all()
        seed_rooms()
        db_path = os.path.join(basedir, 'hotel.db')
        print('Database file created (or already exists):', db_path)

    # Start the Flask development server so you can visit the site
    app.run(debug=True)
