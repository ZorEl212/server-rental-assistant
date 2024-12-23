from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from models.baseModel import Base, BaseModel


class User(BaseModel, Base):
    __tablename__ = "users"

    uuid = Column(Text, unique=True, default=None)
    linux_username = Column(Text, unique=True, nullable=False)
    linux_password = Column(Text, nullable=False)
    balance = Column(Integer, default=0)

    # Relationships
    telegram_user = relationship(
        "TelegramUser", back_populates="user", cascade="all, delete"
    )
    rentals = relationship("Rental", back_populates="user", cascade="all, delete")
    payments = relationship("Payment", back_populates="user", cascade="all, delete")

    async def update_balance(self, amount, transaction_type):
        """
        Record a transaction, updating the user's balance.
        :param amount: Amount to credit or debit.
        :param transaction_type: 'payment' or 'refund'.
        """

        if transaction_type == "credit":
            self.balance += amount
        elif transaction_type == "debit":
            if amount > self.balance:
                raise ValueError("Insufficient balance.")
            self.balance += amount
        else:
            raise ValueError("Invalid transaction type.")
