from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from models.baseModel import Base, BaseModel


class User(BaseModel, Base):
    __tablename__ = "users"

    uuid = Column(Text, unique=True, default=None)
    linux_username = Column(Text, unique=True, nullable=False)
    linux_password = Column(Text, nullable=False)

    # Relationships
    telegram_user = relationship(
        "TelegramUser", back_populates="user", cascade="all, delete"
    )
    rentals = relationship("Rental", back_populates="user", cascade="all, delete")
    payments = relationship("Payment", back_populates="user", cascade="all, delete")
