import datetime
from sqlalchemy import Column, Integer, String, Date, Time, Text, TIMESTAMP
from .database import Base

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    hcp_name = Column(String, index=True, nullable=False)
    interaction_type = Column(String)
    interaction_date = Column(Date)
    interaction_time = Column(Time)
    attendees = Column(Text)
    topics_discussed = Column(Text)
    materials_shared = Column(Text)
    observed_sentiment = Column(String)
    outcomes = Column(Text)
    follow_up_actions = Column(Text)
