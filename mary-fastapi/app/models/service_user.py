from sqlalchemy import Column, Integer, String, DateTime, Text, Date, ForeignKey, func, Float
from sqlalchemy.orm import relationship
from app.db.session import Base
import app.models.master_data

class ServiceUser(Base):
    __tablename__ = "m_service_users"

    su_id = Column(Integer, primary_key=True, index=True)
    su_number = Column(String(255), nullable=True)
    first_name = Column("su_first_name", String(255), nullable=False)
    surname = Column("su_last_name", String(255), nullable=False)
    preferred_name = Column(String(255), nullable=True)
    
    phone = Column("contact_number", String(255), nullable=True)
    address = Column("home_address", Text, nullable=True)
    email = Column(String(255), nullable=True)
    
    next_of_kin = Column(String(255), nullable=True)
    nok_address = Column(String(255), nullable=True)
    nok_relationship = Column(Integer, nullable=True)
    nok_contact_number = Column(String(255), nullable=True)
    
    second_contact = Column(String(255), nullable=True)
    second_contact_address = Column(String(255), nullable=True)
    second_contact_number = Column(String(255), nullable=True)
    second_contact_relationship = Column(Integer, nullable=True)
    
    contract = Column(String(255), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    service_start_date = Column(Date, nullable=True)
    service_end_date = Column(Date, nullable=True)
    services_provided = Column(Text, nullable=True)
    medical_history = Column(Text, nullable=True)
    medications_json = Column("medications", Text, nullable=True)
    care_plan_notes = Column("su_notes", Text, nullable=True)
    
    gender_id = Column(Integer, ForeignKey("m_genders.gender_id"), nullable=True)
    religion_id = Column(Integer, ForeignKey("m_religions.religion_id"), nullable=True)
    branch_id = Column(Integer, ForeignKey("m_branches.branch_id"), nullable=True)
    gp_id = Column(Integer, nullable=True)
    nhs_id = Column(Integer, nullable=True)
    service_status_id = Column(Integer, ForeignKey("m_service_statuses.service_status_id"), nullable=True)
    marital_status_id = Column(Integer, ForeignKey("m_marital_statuses.marital_status_id"), nullable=True)
    nationality_id = Column(Integer, ForeignKey("m_nationalities.nationality_id"), nullable=True)
    
    latitude = Column("address_lat", Float, nullable=True)
    longitude = Column("address_long", Float, nullable=True)
    
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    gender = relationship("Gender", lazy="joined")
    service_status = relationship("ServiceStatus", lazy="joined")
    branch = relationship("Branch", lazy="joined")

    @property
    def su_full_name(self) -> str:
        return f"{self.first_name} {self.surname}".strip()
