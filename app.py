"""Online Food Ordering System - Flask application."""
import logging
import os
import re
import secrets
import sqlite3

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from database import get_connection, init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_QTY = 20


def create_app(test_config=None):
    """Application factory. Tests pass their own config (e.g. a temp database)."""
    app = Flask(__name__)
    app.config["DATABASE"] = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "instance", "food.db"))
    # SECRET_KEY comes from the environment. A random fallback keeps local dev easy,
    # but sessions reset on restart, so set SECRET_KEY on a real server.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    if test_config:
        app.config.update(test_config)

    db_dir = os.path.dirname(app.config["DATABASE"])
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    init_db(app.config["DATABASE"])

    def db():
        return get_connection(app.config["DATABASE"])

    # ---------- helpers ----------
    def cart_details():
        """Build cart lines from the session. Prices always come from the database."""
        cart = session.get("cart", {})
        lines, total = [], 0.0
        if not cart:
            return lines, total
        conn = db()
        try:
            for item_id, qty in cart.items():
                row = conn.execute("SELECT * FROM menu_items WHERE id = ?", (int(item_id),)).fetchone()
                if row is None:
                    continue
                subtotal = round(row["price"] * qty, 2)
                lines.append({"item": row, "quantity": qty, "subtotal": subtotal})
                total += subtotal
        finally:
            conn.close()
        return lines, round(total, 2)

    def parse_qty(raw):
        try:
            qty = int(raw)
        except (TypeError, ValueError):
            return None
        return qty if 0 <= qty <= MAX_QTY else None

    @app.context_processor
    def inject_cart_count():
        return {"cart_count": sum(session.get("cart", {}).values())}

    # ---------- routes ----------
    @app.route("/")
    def index():
        search = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()
        query, params = "SELECT * FROM menu_items WHERE 1=1", []
        if search:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY id"
        conn = db()
        try:
            items = conn.execute(query, params).fetchall()
            categories = [r["category"] for r in conn.execute(
                "SELECT DISTINCT category FROM menu_items ORDER BY category")]
        finally:
            conn.close()
        return render_template("index.html", items=items, categories=categories,
                               search=search, selected=category)

    @app.route("/health")
    def health():
        return {"status": "ok"}

    @app.route("/cart")
    def cart():
        lines, total = cart_details()
        return render_template("cart.html", lines=lines, total=total)

    @app.route("/cart/add/<int:item_id>", methods=["POST"])
    def cart_add(item_id):
        conn = db()
        try:
            row = conn.execute("SELECT name FROM menu_items WHERE id = ?", (item_id,)).fetchone()
        finally:
            conn.close()
        if row is None:
            abort(404)
        cart = session.get("cart", {})
        key = str(item_id)
        cart[key] = min(cart.get(key, 0) + 1, MAX_QTY)
        session["cart"] = cart
        flash(f"Added {row['name']} to your cart.", "success")
        return redirect(request.referrer or url_for("index"))

    @app.route("/cart/update/<int:item_id>", methods=["POST"])
    def cart_update(item_id):
        qty = parse_qty(request.form.get("quantity"))
        cart = session.get("cart", {})
        if str(item_id) not in cart:
            abort(404)
        if qty is None:
            flash(f"Quantity must be a whole number from 0 to {MAX_QTY}.", "danger")
        elif qty == 0:
            cart.pop(str(item_id))
            flash("Item removed from cart.", "success")
        else:
            cart[str(item_id)] = qty
            flash("Cart updated.", "success")
        session["cart"] = cart
        return redirect(url_for("cart"))

    @app.route("/cart/remove/<int:item_id>", methods=["POST"])
    def cart_remove(item_id):
        cart = session.get("cart", {})
        if cart.pop(str(item_id), None) is None:
            abort(404)
        session["cart"] = cart
        flash("Item removed from cart.", "success")
        return redirect(url_for("cart"))

    @app.route("/checkout", methods=["GET", "POST"])
    def checkout():
        lines, total = cart_details()
        if not lines:
            flash("Your cart is empty. Add some food first!", "danger")
            return redirect(url_for("index"))

        form = {"name": "", "phone": "", "address": ""}
        if request.method == "POST":
            form = {k: request.form.get(k, "").strip() for k in form}
            errors = validate_order(form)
            if errors:
                for e in errors:
                    flash(e, "danger")
                return render_template("checkout.html", lines=lines, total=total, form=form), 400
            try:
                order_code = save_order(form, lines, total)
            except sqlite3.Error:
                app.logger.exception("Could not save order")
                flash("Sorry, we could not save your order. Please try again.", "danger")
                return render_template("checkout.html", lines=lines, total=total, form=form), 500
            session.pop("cart", None)
            flash("Order placed successfully!", "success")
            return redirect(url_for("confirmation", order_code=order_code))
        return render_template("checkout.html", lines=lines, total=total, form=form)

    def validate_order(form):
        errors = []
        if not 2 <= len(form["name"]) <= 60 or not re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", form["name"]):
            errors.append("Name must be 2-60 letters (spaces, dots, apostrophes and hyphens allowed).")
        if not re.fullmatch(r"[6-9]\d{9}", form["phone"]):
            errors.append("Phone must be a valid 10-digit Indian mobile number.")
        if not 10 <= len(form["address"]) <= 200:
            errors.append("Address must be between 10 and 200 characters.")
        return errors

    def save_order(form, lines, total):
        order_code = "ORD-" + secrets.token_hex(4).upper()
        conn = db()
        try:
            cur = conn.execute(
                "INSERT INTO orders (order_code, customer_name, phone, address, total) VALUES (?, ?, ?, ?, ?)",
                (order_code, form["name"], form["phone"], form["address"], total),
            )
            order_id = cur.lastrowid
            conn.executemany(
                "INSERT INTO order_items (order_id, item_name, unit_price, quantity) VALUES (?, ?, ?, ?)",
                [(order_id, l["item"]["name"], l["item"]["price"], l["quantity"]) for l in lines],
            )
            conn.commit()
        finally:
            conn.close()
        return order_code

    def load_items(conn, order_id):
        return conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()

    @app.route("/confirmation/<order_code>")
    def confirmation(order_code):
        conn = db()
        try:
            order = conn.execute("SELECT * FROM orders WHERE order_code = ?", (order_code,)).fetchone()
            if order is None:
                abort(404)
            items = load_items(conn, order["id"])
        finally:
            conn.close()
        return render_template("confirmation.html", order=order, items=items)

    @app.route("/orders")
    def orders():
        conn = db()
        try:
            rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
            history = [{"order": o, "order_items": load_items(conn, o["id"])} for o in rows]
        finally:
            conn.close()
        return render_template("orders.html", history=history)

    # ---------- error pages (no stack traces shown) ----------
    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("error.html", code=500, message="Something went wrong on our side."), 500

    return app


app = create_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
