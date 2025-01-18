import time

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from models.baseModel import Base, BaseModel


class User(BaseModel, Base):
    """
    User model representing a system user with associated information and balances.

    Attributes:
        uuid (Text): Unique identifier for the user.
        linux_username (Text): Linux system username for the user.
        linux_password (Text): Linux system password for the user.
        balance (Integer): Current balance of the user, defaults to 0.
    """

    __tablename__ = "users"

    uuid = Column(Text, unique=True, default=None)
    linux_username = Column(Text, unique=True, nullable=False)
    linux_password = Column(Text, nullable=False)
    balance = Column(Integer, default=0)
    last_deduction_time = Column(Integer, default=time.time())

    # Relationships
    telegram_user = relationship(
        "TelegramUser", back_populates="user", cascade="all, delete"
    )
    rentals = relationship("Rental", back_populates="user", cascade="all, delete")
    payments = relationship("Payment", back_populates="user", cascade="all, delete")

    async def update_balance(self, amount, transaction_type):
        """
        Update the user's balance by recording a transaction.

        Args:
            amount (int): The amount to be credited or debited.
            transaction_type (str): The type of transaction ('credit' or 'debit').

        Raises:
            ValueError: If an invalid transaction type is provided or if there
                        is an attempt to debit more than the available balance.
        """
        if transaction_type == "credit":
            self.balance += amount
        elif transaction_type == "debit":
            if abs(amount) > self.balance:
                raise ValueError("Insufficient balance.")
            self.balance += amount
        else:
            raise ValueError("Invalid transaction type.")
