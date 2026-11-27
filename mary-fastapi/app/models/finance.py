from sqlalchemy import Column, Integer, String, DateTime, Text, Float, func, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class MPayroll(Base):
    __tablename__ = "m_payrolls"

    payroll_id = Column(Integer, primary_key=True, index=True)
    payroll_number = Column(String(255), nullable=False, index=True)
    tx_id = Column(Integer, ForeignKey("m_transactions.tx_id"), nullable=True)
    payment = Column(DateTime, nullable=True)
    rate = Column(Float, nullable=True)
    generated = Column(Integer, nullable=True)
    processed = Column(Integer, nullable=True)
    date_range = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class MInvoice(Base):
    __tablename__ = "m_invoices"

    invoice_id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(255), nullable=False, index=True)
    tx_id = Column(Integer, ForeignKey("m_transactions.tx_id"), nullable=True)
    payment = Column(DateTime, nullable=True)
    invoice = Column(Float, nullable=True)
    generated = Column(Integer, nullable=True)
    processed = Column(Integer, nullable=True)
    date_range = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
