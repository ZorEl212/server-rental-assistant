from sqlalchemy import create_engine
from sqlalchemy.orm import Query, joinedload, scoped_session, sessionmaker
from sqlalchemy.sql import or_

from models.baseModel import Base
from models.payments import Payment
from models.rentals import Rental
from models.telegram_users import TelegramUser
from models.users import User

classes = {
    "Rental": Rental,
    "Payment": Payment,
    "User": User,
    "TelegramUser": TelegramUser,
}


class DBStorage:
    """
    This class is the storage engine for the application. It uses SQLAlchemy to
    interact with the database and perform CRUD operations on the data.
    """

    __engine = None
    __session = None

    def __init__(self):
        self.__engine = create_engine("sqlite:///server-database.db", echo=False)

    def all(self, cls=None, filters=None):
        """
        Query all objects from the database with optional class and filters.
        If no class is provided, query all objects from all classes.
        If a class is provided but no filters, query all objects of that class.
        If a class and filters are provided, query objects of that class with the given filters.
        :param cls: The class of the object to query (e.g., User, Rental, etc.)
        :param filters: Optional dictionary of filters (e.g., {'column': value})
        :return: A dictionary of objects with the format {'ClassName.id': object} (e.g., {'User.1': <User object>})
        """

        new_dict = {}

        if cls:
            target_class = classes.get(cls) if isinstance(cls, str) else cls
            if target_class not in classes.values():
                raise ValueError(f"Class '{cls}' not found.")

            query = self.__session.query(target_class)
            objs = query.filter_by(**filters).all() if filters else query.all()

            for obj in objs:
                key = f"{obj.__class__.__name__}.{obj.id}"
                new_dict[key] = obj
            return new_dict

        for clss_name, clss in classes.items():
            objs = self.__session.query(clss).all()
            for obj in objs:
                key = f"{obj.__class__.__name__}.{obj.id}"
                new_dict[key] = obj

        return new_dict

    def reload(self):
        """
        Create all tables in the database and initialize a new session.
        :return: None
        """

        Base.metadata.create_all(self.__engine)
        ses_factory = sessionmaker(bind=self.__engine, expire_on_commit=False)
        self.__session = scoped_session(ses_factory)

    def close(self):
        """
        Close the current session and remove it from the engine.
        :return: None
        """
        self.__session.remove()

    def new(self, obj):
        """
        Add the object to the current database session.
        :param obj: The object to add to the session.
        :return: None
        """

        self.__session.add(obj)

    def save(self):
        """
        Commit all changes of the current database session.
        :return: None
        """

        self.__session.commit()

    def delete(self, obj=None):
        """
        Delete an object from the current database session.
        This won't delete the object from the database until the session is saved.
        :param obj: The object to delete. e.g., User, Rental, etc.
        :return: None
        """

        if obj is not None:
            self.__session.delete(obj)

    def get(self, cls, id):
        """
        Get an object from the database based on the class and ID.
        :param cls: The class of the object to query (e.g., User, Rental, etc.)
        :param id: The ID of the object to query.
        :return: The object if found, otherwise None.
        """

        cls = classes[cls] if isinstance(cls, str) else cls
        if cls not in classes.values():
            return None

        all_cls = self.all(cls)
        for value in all_cls.values():
            if value.id == id:
                return value

        return None

    def count(self, cls=None):
        """
        Count the number of objects in the database. If a class is provided, count only objects of that class.
        :param cls: The class of the object to count (e.g., User, Rental, etc.)
        :return: The number of objects in the database. (int)
        """

        all_class = classes.values()

        if not cls:
            count = 0
            for clas in all_class:
                count += len(self.all(clas).values())
        else:
            count = len(self.all(cls).values())

        return count

    def query_object(self, cls, **filters):
        """
        Query an object from the database based on the class and given filters.
        Example: query_object(User, linux_username='john_doe')

        :param cls: The class of the object to query (e.g., User, Rental, etc.)
        :param filters: Any keyword arguments to use as filters (e.g., linux_username='john_doe')
        :return: The first object matching the filters, or None if not found
        """

        cls = classes[cls] if isinstance(cls, str) else cls
        if cls not in classes.values():
            return None  # Return None if the class is not in the list of known classes

        query = self.__session.query(cls)

        # Apply filters dynamically if provided
        for attr, value in filters.items():
            query = query.filter(getattr(cls, attr) == value)

        return query.first()  # Return the first matching result, or None if not found

    def join(
        self, base_cls, related_classes, filters=None, fetch_one=False, outer=False
    ):
        """
        Perform a join query on the database based on the base class and related
        classes, with optional filters and fetch options. This method is useful
        for querying related objects from multiple tables.
        By default, this method performs an inner join on the related classes. To
        perform an outer join, set the 'outer' parameter to True. Helpful for
        fetching related objects even if they don't have a match in the base class.
        Fetch only one result by setting 'fetch_one' to True. This is useful when
        you expect only one result from the query. In this case the object is returned
        directly, instead of a list containing the object.
        Note: This method assumes that the base class has a relationship with the related classes.

        :param fetch_one: Fetch only one result if True, otherwise fetch all results.
        :param base_cls: The base class to query (e.g., User, Rental, etc.).
        :param related_classes: A list of related classes to join (e.g., [User, Rental]).
        :param filters: Optional dictionary of filters (e.g., {'column': value}).
        :param outer: Use an outer join if True; otherwise, use inner join.

        :return: The result of the query (a list of objects). If 'fetch_one' is True, return only one object.
         None if no results found.
        """

        # Start with the base query
        base_cls = classes[base_cls] if isinstance(base_cls, str) else base_cls
        related_classes = [
            classes[cls] if isinstance(cls, str) else cls for cls in related_classes
        ]
        query = self.__session.query(base_cls)

        # Automatically join related classes based on relationships
        for related_cls in related_classes:
            if outer:
                query = query.outerjoin(related_cls)  # Use outer join
            else:
                query = query.join(related_cls)  # Use inner join by default

        # Apply additional filters if provided
        if filters:
            for attr, value in filters.items():
                query = query.filter(getattr(base_cls, attr) == value)

        # Execute the query and return results
        return query.all() if not fetch_one else query.first()
