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
