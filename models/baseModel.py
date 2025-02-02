import uuid
from datetime import datetime

from sqlalchemy import UUID, Column, DateTime, String
from sqlalchemy.orm import declarative_base, relationship

import models

time = "%Y-%m-%dT%H:%M:%S.%f"
# Define the base class for ORM
Base = declarative_base()


# Define the User class
class BaseModel:
    """
    Base class for all models in the ORM.
    """

    id = Column(String(36), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def __init__(self, *args, **kwargs):
        """Initialization of the base model
        Args:
            *args: Unused
            **kwargs: Arbitrary keyword arguments
        """

        if kwargs:
            for key, value in kwargs.items():
                if key != "__class__":
                    setattr(self, key, value)
            if kwargs.get("created_at", None) and type(self.created_at) is str:
                self.created_at = datetime.strptime(kwargs["created_at"], time)
            else:
                self.created_at = datetime.utcnow()
            if kwargs.get("updated_at", None) and type(self.updated_at) is str:
                self.updated_at = datetime.strptime(kwargs["updated_at"], time)
            else:
                self.updated_at = datetime.utcnow()
            if kwargs.get("id", None) is None:
                self.id = str(uuid.uuid4())
        else:
            self.id = str(uuid.uuid4())
            self.created_at = datetime.utcnow()
            self.updated_at = self.created_at

    def __str__(self):
        """String representation of the BaseModel class"""
        return "[{:s}] ({:s}) {}".format(
            self.__class__.__name__, self.id, self.__dict__
        )

    def save(self):
        """
        Save the current instance to the storage. The instance is stored in the current session and
        the session is committed to the database.
        At the moment it should only be used when creating a new instance.
        :return: None
        """

        self.updated_at = datetime.utcnow()
        models.storage.new(self)
        models.storage.save()

    def to_dict(self, save_fs=None):
        """
        Create a dictionary representation of the instance.
        :param save_fs: If True, the password field is not returned.
        :return: A dictionary representation of the instance.
        """
        new_dict = self.__dict__.copy()
        if "created_at" in new_dict:
            new_dict["created_at"] = new_dict["created_at"].strftime(time)
        if "updated_at" in new_dict:
            new_dict["updated_at"] = new_dict["updated_at"].strftime(time)
        new_dict["__class__"] = self.__class__.__name__
        if "_sa_instance_state" in new_dict:
            del new_dict["_sa_instance_state"]
        if save_fs is None:
            if "linux_password" in new_dict:
                del new_dict["linux_password"]
        return new_dict

    def delete(self):
        """
        Delete the current instance from the storage.
        Note: DO NOT use this method at the moment. It is not implemented.
        :return: True if successful, False otherwise.
        """
        models.storage.delete(self)
        models.storage.save()
