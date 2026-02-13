from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# -------------------- APP INIT --------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# -------------------- DATABASE CONFIG --------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# -------------------- USER MODEL --------------------
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

# -------------------- PRODUCT MODEL --------------------
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

# ==================== CUSTOMER LOGIN ====================
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

# ==================== CUSTOMER DASHBOARD ====================
@app.route("/customer-dashboard")
def customer_dashboard():
    if "user_id" not in session or session.get("role") != "customer":
        return redirect(url_for("customer_login"))

    customer = User.query.get(session["user_id"])
    vendors = User.query.filter_by(role="vendor").all()

    products = Product.query.all()

    return render_template(
        "swift_store.html",
        vendors=vendors,
        products=products,
        customer=customer
    )


# ==================== VENDOR LOGIN ====================
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

# ==================== VENDOR DASHBOARD ====================
@app.route("/vendor-dashboard", methods=["GET", "POST"])
def vendor_dashboard():
    if "user_id" not in session or session.get("role") != "vendor":
        return redirect(url_for("vendor_login"))

    vendor = User.query.get(session["user_id"])

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        category = request.form["category"]
        image = request.form["image"]

        new_product = Product(
            name=name,
            price=float(price),
            category=category,
            image=image,
            vendor_id=vendor.id
        )

        db.session.add(new_product)
        db.session.commit()

        return redirect(url_for("vendor_dashboard"))

    products = Product.query.filter_by(vendor_id=vendor.id).all()

    return render_template(
        "vendor_dashboard.html",
        products=products,
        vendor=vendor
    )

# ==================== SAVE VENDOR LOCATION ====================
@app.route("/save-vendor-location", methods=["POST"])
def save_vendor_location():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 403

    vendor = User.query.get(session["user_id"])
    data = request.get_json()

    vendor.latitude = data["latitude"]
    vendor.longitude = data["longitude"]

    db.session.commit()

    return jsonify({"success": True})

# ==================== DELETE PRODUCT ====================
@app.route("/delete-product/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    if "user_id" not in session:
        return redirect(url_for("vendor_login"))

    product = Product.query.get_or_404(product_id)

    if product.vendor_id != session["user_id"]:
        return redirect(url_for("vendor_dashboard"))

    db.session.delete(product)
    db.session.commit()

    return redirect(url_for("vendor_dashboard"))

# ==================== DELIVERY LOGIN ====================
@app.route("/delivery-login", methods=["GET", "POST"])
def delivery_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email, role="delivery").first()

        if user and bcrypt.check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["role"] = user.role
            return redirect(url_for("delivery_dashboard"))

        flash("Invalid credentials!")
        return redirect(url_for("delivery_login"))

    return render_template("delivery_login.html")

# ==================== DELIVERY DASHBOARD ====================
@app.route("/delivery-dashboard")
def delivery_dashboard():
    if "user_id" not in session or session.get("role") != "delivery":
        return redirect(url_for("delivery_login"))

    return "<h2>Delivery Dashboard (Coming Soon)</h2>"

# ==================== LOGOUT ====================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("entry"))

# ==================== REGISTER ====================
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

        # If vendor, allow company fields
        company_name = request.form.get("company_name")
        address = request.form.get("address")

        new_user = User(
            email=email,
            password=hashed_password,
            role=role,
            company_name=company_name,
            address=address
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please login.")
        return redirect(url_for(f"{role}_login"))

    return render_template("register.html", role=role)

# ==================== RUN ====================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
