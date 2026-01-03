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

    admissions = relationship("Admission", back_populates="patient")
    transfers = relationship("Transfer", back_populates="patient")
    icu_stays = relationship("ICUStay", back_populates="patient")

class Admission(Base):
    __tablename__ = "admissions"
    
    hadm_id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("patients.subject_id"), index=True)
    admittime = Column(DateTime)
    dischtime = Column(DateTime)
    deathtime = Column(DateTime, nullable=True) 
    admission_type = Column(String(50))
    admit_provider_id = Column(String(50)) 
    admission_location = Column(String(50))
    discharge_location = Column(String(50))
    insurance = Column(String(255))
    language = Column(String(50)) 
    marital_status = Column(String(50)) 
    race = Column(String(100)) # Renamed from ethnicity to match CSV
    edregtime = Column(DateTime, nullable=True) 
    edouttime = Column(DateTime, nullable=True) 
    hospital_expire_flag = Column(Integer, default=0) # Changed to Int to match CSV 0/1

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
    eventtype = Column(String(50)) 
    careunit = Column(String(50))
    intime = Column(DateTime)
    outtime = Column(DateTime)

    patient = relationship("Patient", back_populates="transfers")
    admission = relationship("Admission", back_populates="transfers")

# ==========================================
# MODULE: HOSP
# ==========================================

class DiagnosisICD(Base):
    __tablename__ = "diagnoses_icd"
    
    # Synthetic PK for SQLAlchemy management
    id = Column(Integer, primary_key=True, autoincrement=True) 
    subject_id = Column(Integer, ForeignKey("patients.subject_id"))
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"))
    seq_num = Column(Integer)
    icd_code = Column(String(10), index=True)
    icd_version = Column(Integer)

    admission = relationship("Admission", back_populates="diagnoses")

class ProcedureICD(Base):
    __tablename__ = "procedures_icd"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("patients.subject_id"))
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"))
    seq_num = Column(Integer)
    chartdate = Column(DateTime) 
    icd_code = Column(String(10), index=True)
    icd_version = Column(Integer)

    admission = relationship("Admission", back_populates="procedures")

class Prescription(Base):
    __tablename__ = "prescriptions"
    
    # Synthetic PK
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("patients.subject_id"))
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"))
    pharmacy_id = Column(Integer, nullable=True) 
    poe_id = Column(String(50), nullable=True) 
    poe_seq = Column(Integer, nullable=True) 
    order_provider_id = Column(String(50), nullable=True) 
    starttime = Column(DateTime)
    stoptime = Column(DateTime)
    drug_type = Column(String(50))
    drug = Column(String(255), index=True)
    formulary_drug_cd = Column(String(50)) 
    gsn = Column(String(255)) 
    ndc = Column(String(50)) 
    prod_strength = Column(String(255)) 
    form_rx = Column(String(50)) 
    dose_val_rx = Column(String(50))
    dose_unit_rx = Column(String(50))
    form_val_disp = Column(String(50)) 
    form_unit_disp = Column(String(50)) 
    doses_per_24_hrs = Column(Integer, nullable=True) 
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
    
    labevent_id = Column(Integer, primary_key=True, index=True) 
    subject_id = Column(Integer, ForeignKey("patients.subject_id"))
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"), nullable=True)
    specimen_id = Column(Integer, nullable=True) 
    itemid = Column(Integer, ForeignKey("d_labitems.itemid"))
    order_provider_id = Column(String(50), nullable=True) 
    charttime = Column(DateTime)
    storetime = Column(DateTime, nullable=True) 
    value = Column(String(255)) 
    valuenum = Column(Numeric(10, 4))
    valueuom = Column(String(20))
    ref_range_lower = Column(Numeric(10, 4), nullable=True) 
    ref_range_upper = Column(Numeric(10, 4), nullable=True) 
    flag = Column(String(20))
    priority = Column(String(20)) 
    comments = Column(Text, nullable=True) 

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
    first_careunit = Column(String(50))
    last_careunit = Column(String(50))
    intime = Column(DateTime)
    outtime = Column(DateTime)
    los = Column(Numeric(10, 4))

    patient = relationship("Patient", back_populates="icu_stays")
    admission = relationship("Admission", back_populates="icu_stays")
    chartevents = relationship("ChartEvent", back_populates="icustay")

class ChartEvent(Base):
    __tablename__ = "chartevents"
    
    # No single PK in CSV, using synthetic ID or composite. Using synthetic for ease.
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("patients.subject_id"))
    hadm_id = Column(Integer, ForeignKey("admissions.hadm_id"))
    stay_id = Column(Integer, ForeignKey("icustays.stay_id"))
    caregiver_id = Column(Integer, nullable=True) 
    charttime = Column(DateTime)
    storetime = Column(DateTime) 
    itemid = Column(Integer) 
    value = Column(String(255)) 
    valuenum = Column(Numeric(10, 4))
    valueuom = Column(String(50))
    warning = Column(Integer, default=0) 

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