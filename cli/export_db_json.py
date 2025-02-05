import json
import sqlite3
from datetime import datetime


def sqlite_to_json(db_path="server-database.db"):
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Access columns by name
    cursor = conn.cursor()

    # Get all tables
    tables = ["users", "payments", "telegram_users", "rentals"]

    # Dictionary to hold all data
    all_data = {}

    for table in tables:
        # Get all rows from the table
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()

        # Convert rows to dictionaries
        table_data = []
        for row in rows:
            row_dict = dict(row)

            # Convert datetime objects to ISO format strings
            for key in row_dict:
                if isinstance(row_dict[key], datetime):
                    row_dict[key] = row_dict[key].isoformat()

                # Convert boolean integers to actual booleans
                if key in [
                    "deleted",
                    "is_expired",
                    "is_active",
                    "sent_expiry_notification",
                    "is_zombie",
                ]:
                    row_dict[key] = bool(row_dict[key])

            table_data.append(row_dict)

        all_data[table] = table_data

    # Write to JSON file
    with open("database_export.json", "w") as f:
        json.dump(all_data, f, indent=2, default=str)

    # Close connection
    conn.close()
    print("Export completed successfully!")


if __name__ == "__main__":
    sqlite_to_json()
