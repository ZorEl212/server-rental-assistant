import time
from models.baseModel import Base, BaseModel
from sqlalchemy import Column, String, Text, Integer, ForeignKey, CheckConstraint, REAL
from sqlalchemy.orm import relationship


class Payment(BaseModel, Base):
    __tablename__ = "payments"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(REAL, nullable=False)
    currency = Column(Text, CheckConstraint("currency IN ('INR', 'USD')"), nullable=False)
    payment_date = Column(Integer, nullable=False)

    # Relationships
    user = relationship("User", back_populates="payments")

    def __init__(self, user_id, amount, currency, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = float(amount)
        self.currency = currency
        self.payment_date = int(time.time())

    async def process_payment(self, amount_str=None, currency=None):
        """
        Converts the payment amount to INR if needed and updates the amount.
        Returns the converted amount for verification or further use.
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
        """Asynchronous factory method for creating a Payment instance."""
        instance = cls(user_id, amount, currency, **kwargs)
        await instance.process_payment()
        return instance

    async def record_transaction(self, amount_str, currency, transaction_type):
        pass
