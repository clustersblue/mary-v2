from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Float, func, Time
from sqlalchemy.orm import relationship
from app.db.session import Base

# Model for mary_api_db_new.m_shifts (Care Planner Master Catalog)
class MShift(Base):
    __tablename__ = "m_shifts"

    id = Column("shift_id", Integer, primary_key=True, index=True)
    shift_name = Column("shift", String(255), nullable=False)
    service = Column(Integer, nullable=True)
    shift_type = Column(Integer, nullable=True)
    shift_color = Column(String(20), nullable=True)
    
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Model for mary_api_db_new.dtr_shifts (DTR Work Shifts Configuration)
class DtrShift(Base):
    __tablename__ = "dtr_shifts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shift_code = Column(String(255), nullable=False, unique=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    crosses_midnight = Column(Boolean, default=False)
    break_start = Column(Time, nullable=True)
    break_end = Column(Time, nullable=True)
    grace_period = Column(Integer, default=0)
    night_diff_from = Column(Time, nullable=True)
    night_diff_to = Column(Time, nullable=True)
    is_flexible = Column(Boolean, default=False)
    is_rotating = Column(Boolean, default=False)
    shift_color = Column(String(20), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class MAttendance(Base):
    __tablename__ = "m_attendances"

    id = Column(Integer, primary_key=True, index=True)
    tx_id = Column(Integer, ForeignKey("m_transactions.tx_id"), nullable=True)
    time_in = Column(DateTime, nullable=True)
    time_out = Column(DateTime, nullable=True)
    
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class DtrUserShift(Base):
    __tablename__ = "dtr_user_shifts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    su_id = Column(Integer, ForeignKey("m_service_users.su_id"), nullable=True)
    shift_id = Column(Integer, ForeignKey("dtr_shifts.id"), nullable=True)
    branch_id = Column(Integer, nullable=True)
    
    start_date = Column(String(20), nullable=False) # e.g. "2026-10-02"
    end_date = Column(String(20), nullable=True)   # e.g. "2026-12-31"
    start_time = Column(String(10), nullable=True) # Manual override e.g. "08:30"
    end_time = Column(String(10), nullable=True)   # Manual override e.g. "14:45"
    rrule_str = Column(String(255), nullable=True) # RRULE string e.g. "FREQ=WEEKLY;BYDAY=MO,WE,FR"
    recurrence_rule = Column(String(255), nullable=True)
    recurrence_exception = Column(Text, nullable=True)
    recurrence_id = Column(Integer, nullable=True)
    doubleup = Column(Boolean, default=False)
    status = Column(String(50), default="scheduled") # scheduled, completed, cancelled
    
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    carer = relationship("User", lazy="joined")
    service_user = relationship("ServiceUser", lazy="joined")
    shift_template = relationship("DtrShift", lazy="joined")

class Transaction(Base):
    __tablename__ = "m_transactions"

    tx_id = Column(Integer, primary_key=True, index=True)
    su_id = Column(Integer, ForeignKey("m_service_users.su_id"), nullable=True)
    event_id = Column(Integer, nullable=True)
    user_id = Column("id", Integer, ForeignKey("users.id"), nullable=True)
    shift_id = Column(Integer, ForeignKey("m_shifts.shift_id"), nullable=True)
    
    start = Column(DateTime, nullable=True)
    end = Column(DateTime, nullable=True)
    rate = Column(Float, nullable=True)
    payroll = Column(String(225), nullable=True)
    invoice = Column(String(225), nullable=True)
    doubleup = Column(Boolean, default=False)
    recurrence_id = Column(Integer, nullable=True)
    following_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    carer = relationship("User", lazy="joined")
    service_user = relationship("ServiceUser", lazy="joined")
    shift_template = relationship("MShift", lazy="joined")
    attendance = relationship("MAttendance", primaryjoin="Transaction.tx_id == MAttendance.tx_id", foreign_keys="MAttendance.tx_id", uselist=False, lazy="joined")

class DtrShiftOccurrence(Base):
    __tablename__ = "dtr_shift_occurrences"

    id = Column(Integer, primary_key=True, index=True)
    user_shift_id = Column(Integer, ForeignKey("dtr_user_shifts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("m_shifts.shift_id"), nullable=False)
    branch_id = Column(Integer, nullable=True)
    leave_type_id = Column(Integer, nullable=True)
    leave_type = Column(String(255), nullable=True)
    occurrence_date = Column(String(20), nullable=False)
    is_exception = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    carer = relationship("User", lazy="joined")
    shift = relationship("MShift", lazy="joined")
    service_users_assoc = relationship("DtrOccurrenceServiceUser", lazy="joined", cascade="all, delete-orphan")

class DtrOccurrenceServiceUser(Base):
    __tablename__ = "dtr_occurrence_service_users"

    id = Column(Integer, primary_key=True, index=True)
    shift_occurrence_id = Column(Integer, ForeignKey("dtr_shift_occurrences.id"), nullable=False)
    su_id = Column(Integer, ForeignKey("m_service_users.su_id"), nullable=False)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    clock_in = Column(DateTime, nullable=True)
    clock_out = Column(DateTime, nullable=True)

    service_user = relationship("ServiceUser", lazy="joined")
