from models.baseModel import Base, BaseModel
from sqlalchemy import Column, String, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship


class TelegramUser(BaseModel, Base):
    __tablename__ = "telegram_users"

    tg_user_id = Column(Integer, unique=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tg_username = Column(Text, default=None)
    tg_first_name = Column(Text, default=None)
    tg_last_name = Column(Text, default=None)

    # Relationships
    user = relationship("User", back_populates="telegram_user")
