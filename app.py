from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import math
import requests
import os

# -------------------- APP INIT --------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# -------------------- DATABASE CONFIG --------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# -------------------- GLOBAL CACHE --------------------
reverse_geocode_cache = {}

# -------------------- DISTANCE FUNCTION --------------------
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # km

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c

# -------------------- REVERSE GEOCODING --------------------
def get_address_from_coordinates(lat, lon):
    key = f"{round(lat, 4)}_{round(lon, 4)}"

    if key in reverse_geocode_cache:
        return reverse_geocode_cache[key]

    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        response = requests.get(
            url,
            headers={"User-Agent": "swiftstore-app"},
            timeout=5
        )
        data = response.json()
        address = data.get("display_name", "Address not found")
    except:
        address = "Address lookup failed"

    reverse_geocode_cache[key] = address
    return address

# -------------------- MODELS --------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    company_name = db.Column(db.String(150))
    address = db.Column(db.String(300))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    products = db.relationship('Product', backref='vendor', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(500), nullable=False)

    vendor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# -------------------- HOME --------------------
@app.route("/")
def entry():
    return render_template("entry.html")

# -------------------- CUSTOMER LOGIN --------------------
@app.route("/customer-login", methods=["GET", "POST"])
def customer_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email, role="customer").first()

        if user and bcrypt.check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["role"] = user.role
            return redirect(url_for("customer_dashboard"))

        flash("Invalid credentials!")
        return redirect(url_for("customer_login"))

    return render_template("customer_login.html")

# -------------------- CUSTOMER DASHBOARD --------------------
@app.route("/customer-dashboard")
def customer_dashboard():

    if "user_id" not in session or session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    customer = User.query.get(session["user_id"])
    products = Product.query.all()

    enriched_products = []

    for product in products:
        vendor = product.vendor

        if (
            customer.latitude is not None and
            customer.longitude is not None and
            vendor.latitude is not None and
            vendor.longitude is not None
        ):
            distance = calculate_distance(
                customer.latitude,
                customer.longitude,
                vendor.latitude,
                vendor.longitude
            )
        else:
            distance = 9999

        enriched_products.append({
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "category": product.category,
            "image": product.image,
            "vendor_name": vendor.company_name,
            "vendor_address": vendor.address,
            "distance": round(distance, 2)
        })

    enriched_products.sort(key=lambda x: x["distance"])

    return render_template(
        "swift_store.html",
        products=enriched_products,
        customer=customer
    )

# -------------------- SAVE CUSTOMER LOCATION --------------------
@app.route("/save-customer-location", methods=["POST"])
def save_customer_location():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 403

    customer = User.query.get(session["user_id"])
    data = request.get_json()

    customer.latitude = data["latitude"]
    customer.longitude = data["longitude"]
    customer.address = get_address_from_coordinates(
        customer.latitude,
        customer.longitude
    )

    db.session.commit()
    return jsonify({"success": True})

# -------------------- VENDOR LOGIN --------------------
@app.route("/vendor-login", methods=["GET", "POST"])
def vendor_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email, role="vendor").first()

        if user and bcrypt.check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["role"] = user.role
            return redirect(url_for("vendor_dashboard"))

        flash("Invalid credentials!")
        return redirect(url_for("vendor_login"))

    return render_template("vendor_login.html")

# -------------------- VENDOR DASHBOARD --------------------
@app.route("/vendor-dashboard", methods=["GET", "POST"])
def vendor_dashboard():

    if "user_id" not in session or session.get("role") != "vendor":
        return redirect(url_for("vendor_login"))

    vendor = User.query.get(session["user_id"])

    if request.method == "POST":
        new_product = Product(
            name=request.form["name"],
            price=float(request.form["price"]),
            category=request.form["category"],
            image=request.form["image"],
            vendor_id=vendor.id
        )
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for("vendor_dashboard"))

    products = Product.query.filter_by(vendor_id=vendor.id).all()
    return render_template("vendor_dashboard.html", products=products, vendor=vendor)

# -------------------- SAVE VENDOR LOCATION --------------------
@app.route("/save-vendor-location", methods=["POST"])
def save_vendor_location():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 403

    vendor = User.query.get(session["user_id"])
    data = request.get_json()

    vendor.latitude = data["latitude"]
    vendor.longitude = data["longitude"]
    vendor.address = get_address_from_coordinates(
        vendor.latitude,
        vendor.longitude
    )

    db.session.commit()
    return jsonify({"success": True})

# -------------------- NEARBY VENDORS --------------------
@app.route("/nearby-vendors")
def nearby_vendors():

    if "user_id" not in session or session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    customer = User.query.get(session["user_id"])

    if customer.latitude is None or customer.longitude is None:
        return "Customer location not set."

    vendors = User.query.filter_by(role="vendor").all()
    nearby_list = []

    for vendor in vendors:
        if vendor.latitude is not None and vendor.longitude is not None:
            distance = calculate_distance(
                customer.latitude,
                customer.longitude,
                vendor.latitude,
                vendor.longitude
            )

            if distance <= 5:
                nearby_list.append({
                    "company_name": vendor.company_name,
                    "address": vendor.address,
                    "latitude": vendor.latitude,
                    "longitude": vendor.longitude,
                    "distance": round(distance, 2)
                })

    nearby_list.sort(key=lambda x: x["distance"])

    return render_template("nearby_vendors.html", vendors=nearby_list)

# -------------------- LOGOUT --------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("entry"))

# -------------------- REGISTER --------------------
@app.route("/register/<role>", methods=["GET", "POST"])
def register(role):
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered!")
            return redirect(url_for(f"{role}_login"))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(
            email=email,
            password=hashed_password,
            role=role,
            company_name=request.form.get("company_name"),
            address=request.form.get("address")
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please login.")
        return redirect(url_for(f"{role}_login"))

    return render_template("register.html", role=role)

# -------------------- RUN --------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
