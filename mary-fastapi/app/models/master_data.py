from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, Date, UniqueConstraint, func
from app.db.session import Base

def _note_timestamp(*_args):
    return datetime.now().replace(microsecond=0)

class Gender(Base):
    __tablename__ = "m_genders"
    gender_id = Column(Integer, primary_key=True, index=True)
    gender_name = Column("gender", String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Religion(Base):
    __tablename__ = "m_religions"
    religion_id = Column(Integer, primary_key=True, index=True)
    religion_name = Column("religion", String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Nationality(Base):
    __tablename__ = "m_nationalities"
    nationality_id = Column(Integer, primary_key=True, index=True)
    nationality_name = Column("nationality", String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class MaritalStatus(Base):
    __tablename__ = "m_marital_statuses"
    marital_status_id = Column(Integer, primary_key=True, index=True)
    status_name = Column("marital_status", String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Relation(Base):
    __tablename__ = "m_relations"
    relation_id = Column(Integer, primary_key=True, index=True)
    relation_name = Column("relation", String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class CarerStatus(Base):
    __tablename__ = "m_carer_statuses"
    carer_status_id = Column(Integer, primary_key=True, index=True)
    status_name = Column("carer_status", String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ServiceStatus(Base):
    __tablename__ = "m_service_statuses"
    service_status_id = Column(Integer, primary_key=True, index=True)
    status_name = Column("service_status", String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ResidentStatus(Base):
    __tablename__ = "m_resident_statuses"
    resident_status_id = Column(Integer, primary_key=True, index=True)
    status_name = Column("resident_status", String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ContractType(Base):
    __tablename__ = "m_contract_types"
    contract_type_id = Column(Integer, primary_key=True, index=True)
    type_name = Column("contract_type", String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class EmploymentType(Base):
    __tablename__ = "m_employment_types"
    employment_type_id = Column(Integer, primary_key=True, index=True)
    type_name = Column("employment_type", String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Branch(Base):
    __tablename__ = "m_branches"
    branch_id = Column(Integer, primary_key=True, index=True)
    branch_name = Column("branch", String(255), nullable=False)
    address = Column("branch_address", Text, nullable=True)
    contact_number = Column(String(255), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Service(Base):
    __tablename__ = "m_services"
    service_id = Column(Integer, primary_key=True, index=True)
    service_name = Column("service", String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class PensionScheme(Base):
    __tablename__ = "m_pension_schemes"
    pension_scheme_id = Column(Integer, primary_key=True, index=True)
    scheme_name = Column("pension_scheme", String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class CareType(Base):
    __tablename__ = "m_care_types"
    care_type_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ConditionCategory(Base):
    __tablename__ = "m_condition_categories"
    category_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class MedicalCondition(Base):
    __tablename__ = "m_medical_conditions"
    condition_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class GP(Base):
    __tablename__ = "m_gps"
    gp_id = Column(Integer, primary_key=True, index=True)
    gp_first_name = Column(String(255), nullable=True)
    gp_last_name = Column(String(255), nullable=True)
    gp_address = Column(Text, nullable=True)
    gp_email = Column(String(255), nullable=True)
    gp_contact_number = Column(String(255), nullable=True)
    gp_notes = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class NHS(Base):
    __tablename__ = "m_nhsses"
    nhs_id = Column(Integer, primary_key=True, index=True)
    nhs_first_name = Column(String(255), nullable=True)
    nhs_last_name = Column(String(255), nullable=True)
    nhs_address = Column(Text, nullable=True)
    nhs_email = Column(String(255), nullable=True)
    nhs_contact_number = Column(String(255), nullable=True)
    nhs_notes = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Reference(Base):
    __tablename__ = "m_references"
    reference_id = Column(Integer, primary_key=True, index=True)
    reference_first_name = Column(String(255), nullable=True)
    reference_surname = Column(String(255), nullable=True)
    reference_contact = Column(String(255), nullable=True)
    reference_address = Column(Text, nullable=True)
    reference_relation = Column(String(255), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Requirement(Base):
    __tablename__ = "m_requirements"
    requirement_id = Column(Integer, primary_key=True, index=True)
    requirement = Column(String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class RequirementStatus(Base):
    __tablename__ = "m_requirement_statuses"
    requirement_status_id = Column(Integer, primary_key=True, index=True)
    requirement_status = Column(String(255), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class TrainingCourse(Base):
    __tablename__ = "m_training_courses"
    training_course_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration_hours = Column(String(45), nullable=True)
    validity_months = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ServiceUserRate(Base):
    __tablename__ = "m_service_user_rates"
    id = Column(Integer, primary_key=True, index=True)
    su_id = Column(Integer, nullable=True)
    shift_id = Column(Integer, nullable=True)
    rate = Column(Float, nullable=True)
    invoice = Column(Float, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class MNotes(Base):
    __tablename__ = "m_notes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    su_id = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_note_timestamp)
    updated_at = Column(DateTime, default=_note_timestamp, onupdate=_note_timestamp)

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id = Column(Integer, primary_key=True, index=True)
    file_number = Column(String(255), nullable=True)
    filename = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class PatientCondition(Base):
    __tablename__ = "m_patient_conditions"
    patient_condition_id = Column(Integer, primary_key=True, index=True)
    su_id = Column(Integer, nullable=False, index=True)
    condition_id = Column(Integer, nullable=True)
    category_id = Column(Integer, nullable=True)
    diagnosis_date = Column(Date, nullable=True)
    is_primary = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class PatientCareType(Base):
    """One row for each home-care type assigned to a service user.

    A person can have several types. The same type is stored once.
    """
    __tablename__ = "m_patient_care_types"
    __table_args__ = (
        UniqueConstraint("su_id", "care_type_id", name="uq_patient_care_su_type"),
    )
    patient_care_type_id = Column(Integer, primary_key=True, index=True)
    su_id = Column(Integer, nullable=False, index=True)
    care_type_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class RequirementUserStatus(Base):
    __tablename__ = "m_requirements_status"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    requirement_id = Column(Integer, nullable=False)
    status = Column(Integer, default=0)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
