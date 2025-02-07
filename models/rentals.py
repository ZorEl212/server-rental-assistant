import time

from sqlalchemy import (
    DECIMAL,
    REAL,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from models.baseModel import Base, BaseModel


class Rental(BaseModel, Base):
    """
    Represents a rental record for a user.

    This class stores details about user rentals, including duration, amount, currency,
    and rental state (e.g., active or expired). It also includes methods to modify and manage
    rental plans.

    Attributes:
        user_id (str): Foreign key linking to the user's ID.
        telegram_id (int): Foreign key linking to the user's Telegram ID.
        start_time (int): Unix timestamp indicating the start of the rental.
        end_time (int): Unix timestamp indicating the end of the rental.
        plan_duration (int): Duration of the rental plan in seconds.
        amount (float): Amount paid for the rental.
        currency (str): Currency used for payment ("INR" or "USD").
        is_expired (int): Indicates if the rental has expired (0 for no, 1 for yes).
        is_active (int): Indicates if the rental is active (0 for no, 1 for yes).
        sent_expiry_notification (int): Indicates if the expiry notification has been sent (0 for no, 1 for yes).
        price_rate (float): Price rate applied to the rental.

    Relationships:
        user: Relationship linking to the User table.
        telegram_user: Relationship linking to the TelegramUser table.
    """

    __tablename__ = "rentals"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    telegram_user = Column(
        String,
        ForeignKey("telegram_users.id", ondelete="SET NULL"),
        default=None,
    )
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer, nullable=False)
    plan_duration = Column(Integer, nullable=False)
    amount = Column(DECIMAL, nullable=False)
    currency = Column(
        Text, CheckConstraint("currency IN ('INR', 'USD')"), nullable=False
    )
    is_expired = Column(Integer, CheckConstraint("is_expired IN (0, 1)"), default=0)
    is_active = Column(Integer, CheckConstraint("is_active IN (0, 1)"), default=1)
    sent_expiry_notification = Column(
        Integer, CheckConstraint("sent_expiry_notification IN (0, 1)"), default=0
    )
    price_rate = Column(REAL, nullable=False)
    is_zombie = Column(Integer, CheckConstraint("is_zombie IN (0, 1)"), default=0)

    # Relationships
    user = relationship("User", back_populates="rentals")
    tguser = relationship("TelegramUser", back_populates="rentals")

    async def modify_plan_duration(self, duration_change_seconds, action="reduced"):
        """
        Modifies the rental plan duration by adjusting the end time.

        Args:
            duration_change_seconds (int): The number of seconds to add or subtract from the plan duration.
            action (str): Specifies the action ("reduced" or "extended"). Defaults to "reduced".

        Returns:
            None

        Note:
            If the new end time is in the past and the action is "reduced", no changes are made.
        """
        if self.end_time < int(time.time()):
            self.end_time = int(time.time())
        new_expiry_time = self.end_time + duration_change_seconds

        if new_expiry_time < int(time.time()) and action == "reduced":
            return
        self.end_time = new_expiry_time
        self.plan_duration += duration_change_seconds

    async def extend_plan(self, additional_seconds):
        """
        Extends the rental plan duration by a specified number of seconds.

        Args:
            additional_seconds (int): The number of seconds to add to the plan duration.

        Returns:
            None

        Side Effects:
            Resets the expiry notification flag and sets the rental to active and not expired.
        """
        await self.modify_plan_duration(additional_seconds, action="extended")
        self.sent_expiry_notification = 0
        self.is_expired = 0
        self.save()

    async def reduce_plan(self, reduced_duration_seconds):
        """
        Reduces the rental plan duration by a specified number of seconds.

        Args:
            reduced_duration_seconds (int): The number of seconds to subtract from the plan duration.

        Returns:
            None

        Side Effects:
            Updates the end time and saves the changes to the database.
        """
        await self.modify_plan_duration(-reduced_duration_seconds, action="reduced")
        self.save()
