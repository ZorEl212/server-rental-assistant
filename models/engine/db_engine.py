from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, Query

from models.baseModel import Base
from models.users import User
from models.rentals import Rental
from models.payments import Payment
from models.telegram_users import TelegramUser

classes = {'Rental': Rental, 'Payment': Payment, 'User': User, 'TelegramUser': TelegramUser}

class DBStorage:
    __engine = None
    __session = None
    def __init__(self):
        self.__engine = create_engine("sqlite:///server-database.db", echo=False)

    def all(self, cls=None, filters=None):
        """Query objects from the database with optional class and filters."""
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
        Base.metadata.create_all(self.__engine)
        ses_factory = sessionmaker(bind=self.__engine, expire_on_commit=False)
        self.__session = scoped_session(ses_factory)

    def close(self):
        """call remove() method on the private session attribute"""
        self.__session.remove()

    def new(self, obj):
        """add the object to the current database session"""
        self.__session.add(obj)

    def save(self):
        """commit all changes of the current database session"""
        self.__session.commit()

    def delete(self, obj=None):
        """delete from the current database session obj if not None"""
        if obj is not None:
            self.__session.delete(obj)

    def get(self, cls, id):
        """
        Returns the object based on the class name and its ID, or
        None if not found
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
        count the number of objects in storage
        """
        all_class = classes.values()

        if not cls:
            count = 0
            for clas in all_class:
                count += len(self.all(clas).values())
        else:
            count = len(self.all(cls).values())

        return count

