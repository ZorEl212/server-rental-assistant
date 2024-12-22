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
