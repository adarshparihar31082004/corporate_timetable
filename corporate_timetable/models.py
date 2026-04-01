from sqlalchemy import Column, Integer, String, Text
from database import Base


class PlannerRecord(Base):
    __tablename__ = "planner_records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    organization = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    team = Column(String(255), nullable=True)
    week_range = Column(String(255), nullable=True)
    prepared_by = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    logo_path = Column(String(500), nullable=True)
    rows_json = Column(Text, nullable=False)