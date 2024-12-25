import time
from models.baseModel import Base, BaseModel
from sqlalchemy import Column, String, Text, Integer, ForeignKey, CheckConstraint, REAL
from sqlalchemy.orm import relationship


class Payment(BaseModel, Base):
    """
    Represents a payment made by a user, including details such as the amount, currency, and payment date.

    Attributes:
        user_id (str): The ID of the user making the payment, linked to the Users table.
        amount (float): The payment amount.
        currency (str): The currency of the payment, restricted to 'INR' or 'USD'.
        payment_date (int): The timestamp of when the payment was made.
        user (relationship): Relationship to the User table for retrieving user details.
    """

    __tablename__ = "payments"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(REAL, nullable=False)
    currency = Column(
        Text, CheckConstraint("currency IN ('INR', 'USD')"), nullable=False
    )
    payment_date = Column(Integer, nullable=False)

    # Relationships
    user = relationship("User", back_populates="payments")

    def __init__(self, user_id, amount, currency, **kwargs):
        """
        Initializes a Payment instance.

        Args:
            user_id (str): The ID of the user making the payment.
            amount (float): The payment amount.
            currency (str): The currency of the payment, either 'INR' or 'USD'.
            **kwargs: Additional keyword arguments for the BaseModel.
        """
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = float(amount)
        self.currency = currency
        self.payment_date = int(time.time())

    async def process_payment(self):
        """
        Converts the payment amount to INR if needed and updates the amount.
        Returns the converted amount for verification or further use.

        Returns:
            float: The converted payment amount in INR.

        Raises:
            ValueError: If the currency is not supported.
        """
        if self.currency == "USD":
            from models.misc import Utilities

            exchange_rate = await Utilities.get_exchange_rate("USD", "INR")
            self.amount = self.amount * exchange_rate
            self.currency = "INR"  # Normalize to INR

        elif self.currency == "INR":
            # No conversion needed
            pass

        else:
            raise ValueError("Unsupported currency")

        return self.amount

    @classmethod
    async def create(cls, user_id, amount, currency, **kwargs):
        """
        Asynchronous factory method for creating a Payment instance.

        Args:
            user_id (str): The ID of the user making the payment.
            amount (float): The payment amount.
            currency (str): The currency of the payment, either 'INR' or 'USD'.
            **kwargs: Additional keyword arguments for the Payment instance.

        Returns:
            Payment: An instance of the Payment class with the amount processed.
        """
        instance = cls(user_id, amount, currency, **kwargs)
        await instance.process_payment()
        return instance

    async def record_transaction(self, amount_str, currency, transaction_type):
        """
        Placeholder method to record a payment transaction.

        Args:
            amount_str (str): The payment amount as a string.
            currency (str): The currency of the transaction.
            transaction_type (str): The type of transaction (e.g., 'credit', 'debit').
        """
        pass
