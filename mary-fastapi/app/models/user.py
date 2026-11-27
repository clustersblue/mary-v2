from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Date, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.session import Base
import app.models.master_data

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=False)
    surname = Column(String(255), nullable=False)
    username = Column(String(255), unique=True, nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    password = Column(String(255), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    
    gender_id = Column(Integer, ForeignKey("m_genders.gender_id"), nullable=True)
    nationality_id = Column(Integer, ForeignKey("m_nationalities.nationality_id"), nullable=True)
    marital_status_id = Column(Integer, ForeignKey("m_marital_statuses.marital_status_id"), nullable=True)
    resident_status_id = Column(Integer, ForeignKey("m_resident_statuses.resident_status_id"), nullable=True)
    relation_id = Column(Integer, ForeignKey("m_relations.relation_id"), nullable=True)
    carer_status_id = Column(Integer, ForeignKey("m_carer_statuses.carer_status_id"), nullable=True)
    employment_type_id = Column(Integer, ForeignKey("m_employment_types.employment_type_id"), nullable=True)
    contract_type_id = Column(Integer, ForeignKey("m_contract_types.contract_type_id"), nullable=True)
    pension_scheme_id = Column(Integer, ForeignKey("m_pension_schemes.pension_scheme_id"), nullable=True)
    branch_id = Column(Integer, ForeignKey("m_branches.branch_id"), nullable=True)
    
    mobile = Column("mobile_number", String(50), nullable=True)
    address = Column("current_address", Text, nullable=True)
    ni_num = Column(String(255), nullable=True)
    employment_start_date = Column(Date, nullable=True)
    employment_history = Column(Text, nullable=True)
    carer_notes = Column(Text, nullable=True)
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_address = Column(String(255), nullable=True)
    emergency_contact_number = Column(String(50), nullable=True)
    
    role = Column(Integer, nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    gender = relationship("Gender", lazy="joined")
    branch = relationship("Branch", lazy="joined")
    carer_status = relationship("CarerStatus", lazy="joined")
