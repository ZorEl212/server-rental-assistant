"""
This module contains the core database storage engine for the application.

The `DBStorage` class provides the interface for interacting with the database using SQLAlchemy.
It supports CRUD (Create, Read, Update, Delete) operations, as well as more advanced querying, such as
joining tables and applying filters. The class works with various models (e.g., `User`, `Payment`, `Rental`,
`TelegramUser`) to manage the application's data.

Key Features:
- `all(cls=None, filters=None)`: Retrieve all objects or filter objects by class and criteria.
- `reload()`: Initialize the database engine and session, creating tables if they don't exist.
- `new(obj)`: Add a new object to the current session.
- `save()`: Commit changes to the database.
- `delete(obj)`: Delete an object from the database.
- `get(cls, id)`: Retrieve an object by its class and ID.
- `count(cls=None)`: Count the number of objects in the database (filtered by class if provided).
- `query_object(cls, **filters)`: Query an object based on class and filters.
- `join(base_cls, related_classes, filters=None, fetch_one=False, outer=False)`: Perform joins across related models with support for inner or outer joins.

This module also includes:
- Model definitions for `User`, `Payment`, `Rental`, and `TelegramUser`.
- A centralized session management system using SQLAlchemy’s scoped session and sessionmaker.

Example usage:
    storage = DBStorage()
    storage.reload()  # Initializes the database and session
    users = storage.all("User")  # Retrieve all User objects
    user = storage.get("User", 1)  # Retrieve a specific User by ID

This engine is designed to abstract away the complexities of database interaction, making it easier
to manage data and maintain the application.
"""
