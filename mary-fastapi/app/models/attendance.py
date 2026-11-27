from sqlalchemy import Column, Integer, String, Date, DateTime, Time, Text, Float, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.session import Base

class DtrAttendance(Base):
    __tablename__ = "dtr_attendances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shift_id = Column(Integer, nullable=True)
    
    attendance_date = Column(Date, nullable=False)
    clock_in = Column(Time, nullable=True)
    clock_out = Column(Time, nullable=True)
    total_hours = Column(Float, nullable=True)
    late_minutes = Column(Integer, default=0)
    undertime_minutes = Column(Integer, default=0)
    overtime_minutes = Column(Integer, default=0)
    is_absent = Column(Integer, default=0)
    leave_type_id = Column(Integer, nullable=True)
    leave_type = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    carer = relationship("User", lazy="joined")
