"""Database helpers: SQLite connection, schema creation and sample data."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS menu_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    price       REAL    NOT NULL CHECK (price > 0),
    emoji       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    order_code       TEXT    NOT NULL UNIQUE,
    customer_name    TEXT    NOT NULL,
    phone            TEXT    NOT NULL,
    address          TEXT    NOT NULL,
    total            REAL    NOT NULL,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS order_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL REFERENCES orders(id),
    item_name  TEXT    NOT NULL,
    unit_price REAL    NOT NULL,
    quantity   INTEGER NOT NULL CHECK (quantity > 0)
);
"""

SAMPLE_MENU = [
    ("Margherita Pizza", "Classic pizza with tomato sauce, mozzarella and fresh basil.", "Pizza", 249.0, "🍕"),
    ("Veggie Burger", "Crispy veg patty with lettuce, tomato and house sauce.", "Burgers", 149.0, "🍔"),
    ("Chicken Biryani", "Fragrant basmati rice cooked with spiced chicken.", "Rice", 289.0, "🍛"),
    ("Paneer Tikka Wrap", "Grilled paneer, onions and mint chutney in a soft wrap.", "Wraps", 169.0, "🌯"),
    ("Pasta Alfredo", "Creamy white-sauce pasta with garlic and herbs.", "Pasta", 219.0, "🍝"),
    ("French Fries", "Golden, crispy and lightly salted.", "Snacks", 99.0, "🍟"),
    ("Chocolate Brownie", "Warm fudgy brownie with chocolate drizzle.", "Desserts", 119.0, "🍫"),
    ("Cold Coffee", "Chilled coffee blended with milk and ice cream.", "Drinks", 129.0, "🥤"),
    ("Masala Dosa", "Crispy dosa stuffed with spiced potato, served with chutney.", "South Indian", 139.0, "🥞"),
    ("Chicken Burger", "Juicy grilled chicken, cheese and crunchy lettuce.", "Burgers", 179.0, "🍔"),
]


def get_connection(db_path):
    """Open a SQLite connection that returns rows like dictionaries."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path):
    """Create tables and insert sample menu items if the menu is empty."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        count = conn.execute("SELECT COUNT(*) FROM menu_items").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO menu_items (name, description, category, price, emoji) "
                "VALUES (?, ?, ?, ?, ?)",
                SAMPLE_MENU,
            )
        conn.commit()
    finally:
        conn.close()
