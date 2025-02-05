import json
import sqlite3
from datetime import datetime


def json_to_sqlite(json_path="../database_export.json", db_path="migrated_data.db"):
    # Load JSON data
    with open(json_path) as f:
        data = json.load(f)

    # Identify active users through their rentals
    active_user_ids = set()
    for rental in data["rentals"]:
        if rental.get("is_active") or rental.get("is_expired"):
            active_user_ids.add(rental["user_id"])

    # Filter related data
    active_data = {
        "users": [u for u in data["users"] if u["id"] in active_user_ids],
        "payments": [p for p in data["payments"] if p["user_id"] in active_user_ids],
        "telegram_users": [
            tu for tu in data["telegram_users"] if tu["user_id"] in active_user_ids
        ],
        "rentals": [r for r in data["rentals"] if r["user_id"] in active_user_ids],
    }

    # Create SQLite database with schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")

    # Create tables
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        uuid VARCHAR(36), 
        linux_username TEXT NOT NULL, 
        linux_password TEXT NOT NULL, 
        balance REAL, 
        last_deduction_time REAL, 
        deleted BOOLEAN, 
        id VARCHAR(36) NOT NULL PRIMARY KEY,
        created_at DATETIME, 
        updated_at DATETIME, 
        UNIQUE (uuid)
    )"""
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS payments (
        user_id VARCHAR(36) NOT NULL,
        amount REAL NOT NULL,
        currency TEXT NOT NULL CHECK (currency IN ('INR', 'USD')),
        payment_date INTEGER NOT NULL,
        id VARCHAR(36) NOT NULL PRIMARY KEY,
        created_at DATETIME,
        updated_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
    )"""
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS telegram_users (
        tg_user_id INTEGER NOT NULL,
        user_id VARCHAR(36) NOT NULL,
        tg_username TEXT,
        tg_first_name TEXT,
        tg_last_name TEXT,
        id VARCHAR(36) NOT NULL PRIMARY KEY,
        created_at DATETIME,
        updated_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
    )"""
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS rentals (
        user_id VARCHAR(36) NOT NULL,
        telegram_user VARCHAR(36),
        start_time INTEGER NOT NULL,
        end_time INTEGER NOT NULL,
        plan_duration INTEGER NOT NULL,
        amount REAL NOT NULL,
        currency TEXT NOT NULL CHECK (currency IN ('INR', 'USD')),
        is_expired BOOLEAN,
        is_active BOOLEAN,
        sent_expiry_notification BOOLEAN,
        price_rate REAL NOT NULL,
        is_zombie BOOLEAN,
        id VARCHAR(36) NOT NULL PRIMARY KEY,
        created_at DATETIME,
        updated_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY(telegram_user) REFERENCES telegram_users (id) ON DELETE SET NULL
    )"""
    )

    # Helper function to convert booleans to 0/1
    def bool_to_int(value):
        return 1 if value else 0

    # Insert data in correct order
    # 1. Users
    for user in active_data["users"]:
        cursor.execute(
            """
            INSERT INTO users VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """,
            (
                user["uuid"],
                user["linux_username"],
                user["linux_password"],
                user["balance"],
                user["last_deduction_time"],
                bool_to_int(user["deleted"]),
                user["id"],
                user["created_at"],
                user["updated_at"],
            ),
        )

    # 2. Telegram Users
    for tg_user in active_data["telegram_users"]:
        cursor.execute(
            """
            INSERT INTO telegram_users VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?
            )
        """,
            (
                tg_user["tg_user_id"],
                tg_user["user_id"],
                tg_user["tg_username"],
                tg_user["tg_first_name"],
                tg_user["tg_last_name"],
                tg_user["id"],
                tg_user["created_at"],
                tg_user["updated_at"],
            ),
        )

    # 3. Payments
    for payment in active_data["payments"]:
        cursor.execute(
            """
            INSERT INTO payments VALUES (
                ?, ?, ?, ?, ?, ?, ?
            )
        """,
            (
                payment["user_id"],
                payment["amount"],
                payment["currency"],
                payment["payment_date"],
                payment["id"],
                payment["created_at"],
                payment["updated_at"],
            ),
        )

    # 4. Rentals
    for rental in active_data["rentals"]:
        cursor.execute(
            """
            INSERT INTO rentals VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """,
            (
                rental["user_id"],
                rental.get("telegram_user"),
                rental["start_time"],
                rental["end_time"],
                rental["plan_duration"],
                rental["amount"],
                rental["currency"],
                bool_to_int(rental["is_expired"]),
                bool_to_int(rental["is_active"]),
                bool_to_int(rental["sent_expiry_notification"]),
                rental["price_rate"],
                bool_to_int(rental["is_zombie"]),
                rental["id"],
                rental["created_at"],
                rental["updated_at"],
            ),
        )

    conn.execute("PRAGMA foreign_keys = ON")

    conn.commit()
    conn.close()
    print(f"Migration complete! {len(active_data['users'])} active users migrated.")


if __name__ == "__main__":
    json_to_sqlite()
