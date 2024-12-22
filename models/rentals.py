import time

from models.baseModel import Base, BaseModel
from sqlalchemy import Column, String, Text, Integer, ForeignKey, CheckConstraint, REAL
from sqlalchemy.orm import relationship


# Rentals Table
class Rental(BaseModel, Base):
    """
    Rental class to store user rental information.
    """
    __tablename__ = "rentals"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    telegram_id = Column(Integer, ForeignKey("telegram_users.tg_user_id", ondelete="SET NULL"), default=None)
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer, nullable=False)
    plan_duration = Column(Integer, nullable=False)
    amount = Column(REAL, nullable=False)
    currency = Column(Text, CheckConstraint("currency IN ('INR', 'USD')"), nullable=False)
    is_expired = Column(Integer, CheckConstraint("is_expired IN (0, 1)"), default=0)
    is_active = Column(Integer, CheckConstraint("is_active IN (0, 1)"), default=1)
    sent_expiry_notification = Column(Integer, CheckConstraint("sent_expiry_notification IN (0, 1)"), default=0)

    # Relationships
    user = relationship("User", back_populates="rentals")
    telegram_user = relationship("TelegramUser")

    async def modify_plan_duration(self, duration_change_seconds, action="reduced"):
        expiry_time = self.end_time
        new_expiry_time = expiry_time + duration_change_seconds

        if new_expiry_time < int(time.time()) and action == "reduced":
            return
        self.end_time = new_expiry_time

    async def extend_plan(self, additional_seconds):
        await self.modify_plan_duration(additional_seconds, action="extended")
        self.sent_expiry_notification = 0
        self.is_expired = 0
        self.save()

    async def reduce_plan(self, reduced_duration_seconds):
        await self.modify_plan_duration(-reduced_duration_seconds, action="reduced")
        self.save()
