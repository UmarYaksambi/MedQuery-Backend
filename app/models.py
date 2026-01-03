from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

# ==========================================
# MODULE: CORE
# ==========================================

class Patient(Base):
    __tablename__ = "patients"
    
    subject_id = Column(Integer, primary_key=True, index=True)
    gender = Column(String(5))
    anchor_age = Column(Integer)
    anchor_year = Column(Integer)
    anchor_year_group = Column(String(50)) 
    dod = Column(DateTime, nullable=True)

    # Relationships
    admissions = relationship("Admission", back_populates="patient")
    transfers = relationship("Transfer", back_populates="patient")
    icu_stays = relationship("ICUStay", back_populates="patient")

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

    # Relationships
    patient = relationship("Patient", back_populates="admissions")
    transfers = relationship("Transfer", back_populates="admission")
    diagnoses = relationship("DiagnosisICD", back_populates="admission")
    procedures = relationship("ProcedureICD", back_populates="admission")
    prescriptions = relationship("Prescription", back_populates="admission")
    labevents = relationship("LabEvent", back_populates="admission")
    icu_stays = relationship("ICUStay", back_populates="admission")

class Transfer(Base):
    __tablename__ = "transfers"
    
    transfer_id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("patients.subject_id"))
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"), nullable=True)
    careunit = Column(String(50))
    intime = Column(DateTime)
    outtime = Column(DateTime)

    # Relationships
    patient = relationship("Patient", back_populates="transfers")
    admission = relationship("Admission", back_populates="transfers")

# ==========================================
# MODULE: HOSP
# ==========================================

class DiagnosisICD(Base):
    __tablename__ = "diagnoses_icd"
    
    # Composite PK via synthetic ID or multi-column PK
    id = Column(Integer, primary_key=True, autoincrement=True) 
    subject_id = Column(Integer, ForeignKey("patients.subject_id"))
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"))
    icd_code = Column(String(10), index=True)
    icd_version = Column(Integer)
    seq_num = Column(Integer)

    admission = relationship("Admission", back_populates="diagnoses")

class ProcedureICD(Base):
    __tablename__ = "procedures_icd"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("patients.subject_id"))
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"))
    icd_code = Column(String(10), index=True)
    icd_version = Column(Integer)
    seq_num = Column(Integer)

    admission = relationship("Admission", back_populates="procedures")

class Prescription(Base):
    __tablename__ = "prescriptions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("patients.subject_id"))
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"))
    drug = Column(String(255), index=True)
    drug_type = Column(String(50))
    starttime = Column(DateTime)
    stoptime = Column(DateTime)
    dose_val_rx = Column(String(50))
    dose_unit_rx = Column(String(50))
    route = Column(String(50))

    admission = relationship("Admission", back_populates="prescriptions")

class DLabItem(Base):
    __tablename__ = "d_labitems"
    
    itemid = Column(Integer, primary_key=True, index=True)
    label = Column(String(255))
    fluid = Column(String(50))
    category = Column(String(50))

    labevents = relationship("LabEvent", back_populates="item")

class LabEvent(Base):
    __tablename__ = "labevents"
    
    labevent_id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("patients.subject_id"))
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"), nullable=True)
    itemid = Column(Integer, ForeignKey("d_labitems.itemid"))
    charttime = Column(DateTime)
    valuenum = Column(Numeric(10, 4))
    valueuom = Column(String(20))
    flag = Column(String(20))

    admission = relationship("Admission", back_populates="labevents")
    item = relationship("DLabItem", back_populates="labevents")

# ==========================================
# MODULE: ICU
# ==========================================

class ICUStay(Base):
    __tablename__ = "icustays"
    
    stay_id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("patients.subject_id"))
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"))
    intime = Column(DateTime)
    outtime = Column(DateTime)
    first_careunit = Column(String(50))
    last_careunit = Column(String(50))

    patient = relationship("Patient", back_populates="icu_stays")
    admission = relationship("Admission", back_populates="icu_stays")
    chartevents = relationship("ChartEvent", back_populates="icustay")

class ChartEvent(Base):
    __tablename__ = "chartevents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("patients.subject_id"))
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"))
    stay_id = Column(Integer, ForeignKey("icustays.stay_id"))
    itemid = Column(Integer) # In MIMIC this links to d_items, simplified here
    charttime = Column(DateTime)
    valuenum = Column(Numeric(10, 4))
    valueuom = Column(String(20))

    icustay = relationship("ICUStay", back_populates="chartevents")

# ==========================================
# MODULE: APP (Internal)
# ==========================================

class QueryHistory(Base):
    __tablename__ = "query_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), default="Dr. Sarah Chen")
    question = Column(Text)
    generated_sql = Column(Text)
    answer_text = Column(Text)
    execution_time_ms = Column(Integer)
    row_count = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)