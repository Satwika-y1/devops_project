"""Automated tests for the Online Food Ordering System."""
import sqlite3

VALID_FORM = {"name": "Asha Rao", "phone": "9876543210", "address": "12 MG Road, Hyderabad"}


def db_rows(app, sql, params=()):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def add(client, item_id, times=1):
    for _ in range(times):
        client.post(f"/cart/add/{item_id}")


# ---------- startup & pages ----------
def test_app_starts_with_test_config(app):
    assert app.config["TESTING"] is True
    assert "test_food.db" in app.config["DATABASE"]


def test_home_page_ok(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"FoodieHub" in r.data


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


# ---------- menu ----------
def test_menu_has_at_least_eight_items(app):
    rows = db_rows(app, "SELECT COUNT(*) AS c FROM menu_items")
    assert rows[0]["c"] >= 8


def test_menu_shows_items_and_prices(client):
    r = client.get("/")
    assert b"Margherita Pizza" in r.data
    assert "₹249.00".encode() in r.data


def test_search_filters_menu(client):
    r = client.get("/?q=biryani")
    assert b"Chicken Biryani" in r.data
    assert b"Margherita Pizza" not in r.data


def test_category_filter(client):
    r = client.get("/?category=Desserts")
    assert b"Chocolate Brownie" in r.data
    assert b"Chicken Biryani" not in r.data


def test_search_with_no_match_shows_message(client):
    r = client.get("/?q=zzzzzz")
    assert r.status_code == 200
    assert b"No food items match" in r.data


def test_sql_injection_attempt_is_harmless(client, app):
    r = client.get("/?q=' OR 1=1; DROP TABLE menu_items; --")
    assert r.status_code == 200
    assert db_rows(app, "SELECT COUNT(*) AS c FROM menu_items")[0]["c"] >= 8


# ---------- cart ----------
def test_add_to_cart_and_total(client):
    add(client, 1, 2)   # Margherita 249 x 2
    add(client, 6)      # Fries 99
    r = client.get("/cart")
    assert r.status_code == 200
    assert "₹597.00".encode() in r.data  # 498 + 99


def test_update_quantity(client):
    add(client, 6)
    r = client.post("/cart/update/6", data={"quantity": "3"}, follow_redirects=True)
    assert "₹297.00".encode() in r.data


def test_update_quantity_zero_removes_item(client):
    add(client, 6)
    r = client.post("/cart/update/6", data={"quantity": "0"}, follow_redirects=True)
    assert b"Your cart is empty" in r.data


def test_update_quantity_invalid_is_rejected(client):
    add(client, 6)
    r = client.post("/cart/update/6", data={"quantity": "abc"}, follow_redirects=True)
    assert b"Quantity must be a whole number" in r.data
    r = client.post("/cart/update/6", data={"quantity": "999"}, follow_redirects=True)
    assert b"Quantity must be a whole number" in r.data


def test_remove_from_cart(client):
    add(client, 1)
    r = client.post("/cart/remove/1", follow_redirects=True)
    assert b"Your cart is empty" in r.data


def test_add_unknown_item_returns_404(client):
    assert client.post("/cart/add/9999").status_code == 404


def test_remove_item_not_in_cart_returns_404(client):
    assert client.post("/cart/remove/1").status_code == 404


# ---------- checkout & orders ----------
def test_checkout_with_empty_cart_redirects(client):
    r = client.get("/checkout")
    assert r.status_code == 302


def test_successful_order_is_saved(client, app):
    add(client, 1, 2)
    add(client, 8)
    r = client.post("/checkout", data=VALID_FORM)
    assert r.status_code == 302
    assert "/confirmation/ORD-" in r.headers["Location"]

    orders = db_rows(app, "SELECT * FROM orders")
    assert len(orders) == 1
    assert orders[0]["customer_name"] == "Asha Rao"
    assert orders[0]["total"] == 249 * 2 + 129  # calculated by the backend
    items = db_rows(app, "SELECT * FROM order_items WHERE order_id = ?", (orders[0]["id"],))
    assert sorted((i["item_name"], i["quantity"]) for i in items) == [
        ("Cold Coffee", 1), ("Margherita Pizza", 2)]


def test_confirmation_page_shows_unique_order_id(client):
    add(client, 6)
    r = client.post("/checkout", data=VALID_FORM, follow_redirects=True)
    assert r.status_code == 200
    assert b"Order placed successfully" in r.data
    assert b"ORD-" in r.data


def test_order_ids_are_unique(client, app):
    for _ in range(2):
        add(client, 6)
        client.post("/checkout", data=VALID_FORM)
    codes = [o["order_code"] for o in db_rows(app, "SELECT order_code FROM orders")]
    assert len(codes) == 2 and len(set(codes)) == 2


def test_cart_cleared_after_order(client):
    add(client, 6)
    client.post("/checkout", data=VALID_FORM)
    assert b"Your cart is empty" in client.get("/cart").data


def test_client_cannot_override_price_or_total(client, app):
    add(client, 6)  # fries cost 99
    client.post("/checkout", data={**VALID_FORM, "total": "1", "price": "1"})
    assert db_rows(app, "SELECT total FROM orders")[0]["total"] == 99


import pytest  # noqa: E402


@pytest.mark.parametrize("bad", [
    {"name": "", "phone": "9876543210", "address": "12 MG Road, Hyderabad"},
    {"name": "A", "phone": "9876543210", "address": "12 MG Road, Hyderabad"},
    {"name": "Asha123", "phone": "9876543210", "address": "12 MG Road, Hyderabad"},
    {"name": "Asha Rao", "phone": "12345", "address": "12 MG Road, Hyderabad"},
    {"name": "Asha Rao", "phone": "1234567890", "address": "12 MG Road, Hyderabad"},
    {"name": "Asha Rao", "phone": "98765abcde", "address": "12 MG Road, Hyderabad"},
    {"name": "Asha Rao", "phone": "9876543210", "address": "short"},
    {"name": "Asha Rao", "phone": "9876543210", "address": "x" * 201},
])
def test_invalid_checkout_rejected_and_nothing_saved(client, app, bad):
    add(client, 1)
    r = client.post("/checkout", data=bad)
    assert r.status_code == 400
    assert db_rows(app, "SELECT COUNT(*) AS c FROM orders")[0]["c"] == 0
    assert b"alert-danger" in r.data


def test_invalid_checkout_keeps_cart(client):
    add(client, 1)
    client.post("/checkout", data={"name": "", "phone": "", "address": ""})
    assert b"Margherita Pizza" in client.get("/cart").data


def test_order_history_lists_saved_orders(client):
    add(client, 3)
    client.post("/checkout", data=VALID_FORM)
    r = client.get("/orders")
    assert r.status_code == 200
    assert b"Chicken Biryani" in r.data
    assert b"Asha Rao" in r.data


def test_order_history_empty(client):
    assert b"No orders yet" in client.get("/orders").data


# ---------- errors ----------
def test_unknown_page_returns_friendly_404(client):
    r = client.get("/does-not-exist")
    assert r.status_code == 404
    assert b"Page not found" in r.data
    assert b"Traceback" not in r.data


def test_unknown_confirmation_returns_404(client):
    assert client.get("/confirmation/ORD-NOPE").status_code == 404


def test_wrong_http_method_returns_405(client):
    assert client.get("/cart/add/1").status_code == 405


# ---------- isolation ----------
def test_tests_use_separate_database(app):
    assert "instance" not in app.config["DATABASE"].replace("\\", "/").split("/")[-2:]
