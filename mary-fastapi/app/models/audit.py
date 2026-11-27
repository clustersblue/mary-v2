from sqlalchemy import Column, Integer, String, DateTime, Text, func
from app.db.session import Base

class AuditLog(Base):
    __tablename__ = "m_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(255), nullable=True)
    su_id = Column(Integer, nullable=True, index=True)
    patient_name = Column(String(255), nullable=True)
    record_type = Column(String(100), nullable=False)  # medical_dossier, mar_chart, care_notes, attendance_notes
    action = Column(String(50), nullable=False)       # READ, VIEW, EXPORT, UPDATE
    details = Column(Text, nullable=True)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
