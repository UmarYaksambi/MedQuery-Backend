from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

# --- CORE MODULE ---

class Patient(Base):
    __tablename__ = "patients"
    subject_id = Column(Integer, primary_key=True, index=True)
    gender = Column(String(5))
    anchor_age = Column(Integer)
    anchor_year = Column(Integer)
    dod = Column(DateTime, nullable=True)

    admissions = relationship("Admission", back_populates="patient")

class Admission(Base):
    __tablename__ = "admissions"
    hadm_id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("patients.subject_id"), index=True)
    admittime = Column(DateTime)
    dischtime = Column(DateTime)
    admission_type = Column(String(50))
    admission_location = Column(String(50))
    discharge_location = Column(String(50))
    insurance = Column(String(255))
    ethnicity = Column(String(50))
    hospital_expire_flag = Column(Boolean, default=False)

    patient = relationship("Patient", back_populates="admissions")
    diagnoses = relationship("DiagnosisICD", back_populates="admission")

# --- HOSP MODULE ---

class DiagnosisICD(Base):
    __tablename__ = "diagnoses_icd"
    # Composite PK handled by SQLAlchemy usually requires mapping, using synthetic ID for simplicity here
    # or defining primary_key=True on multiple columns
    subject_id = Column(Integer, ForeignKey("patients.subject_id"), primary_key=True)
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"), primary_key=True)
    seq_num = Column(Integer, primary_key=True)
    icd_code = Column(String(10), index=True)
    icd_version = Column(Integer)

    admission = relationship("Admission", back_populates="diagnoses")

class LabEvent(Base):
    __tablename__ = "labevents"
    labevent_id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("patients.subject_id"))
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"), nullable=True)
    itemid = Column(Integer, index=True)
    charttime = Column(DateTime)
    valuenum = Column(Numeric(10, 4))
    valueuom = Column(String(20))
    flag = Column(String(20))

# --- APP LOGGING (History) ---

class QueryHistory(Base):
    __tablename__ = "query_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), default="Dr. Sarah Chen") # Mock user
    question = Column(Text)
    generated_sql = Column(Text)
    answer_text = Column(Text)
    execution_time_ms = Column(Integer)
    row_count = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)