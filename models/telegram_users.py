from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models.baseModel import Base, BaseModel


class TelegramUser(BaseModel, Base):
    """
    TelegramUser class to manage Telegram-related user details linked to the system user.
    """

    __tablename__ = "telegram_users"

    tg_user_id = Column(
        Integer,
        nullable=False,
        doc="Telegram ID of the account.",
    )
    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key linking to the system user.",
    )
    tg_username = Column(
        Text, default=None, doc="Optional Telegram username of the user."
    )
    tg_first_name = Column(
        Text, default=None, doc="Optional first name of the Telegram user."
    )
    tg_last_name = Column(
        Text, default=None, doc="Optional last name of the Telegram user."
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="telegram_user",
        doc="Relationship linking TelegramUser to the User model.",
    )
