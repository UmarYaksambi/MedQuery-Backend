# MedQuery Backend - AI Analytics Engine

This is the backend service for MedQuery, a clinical data analytics platform. It uses FastAPI to provide a robust API for natural language querying, RAG (Retrieval-Augmented Generation) capabilities, and secure clinical data management.

## 🔗 Frontend Repository

The React-based dashboard can be found here:
**[MedQuery-Frontend](https://www.google.com/search?q=https://github.com/UmarYaksambi/MedQuery)**

## ✨ Features

* **Text-to-SQL Engine**: Translates natural language into SQL queries for clinical datasets.
* **Hybrid Database Support**: Combines MySQL for relational clinical data and MongoDB for audit logs and history.
* **JWT Security**: Secure endpoint protection with role-based access for doctors and admins.
* **Audit Logging**: Every query and system action is tracked for clinical compliance.
* **RAG Integration**: Specialized endpoints for querying unstructured clinical notes.

## 🛠️ Infrastructure Setup

### 1. MySQL Setup

The backend expects a MySQL instance to store relational clinical data (e.g., MIMIC-IV) and core application data.

* **Create Database**: Create a database named `medquery`.
* **Configuration**: Update the `DATABASE_URL` in your environment variables using the format: `mysql+pymysql://user:password@localhost:3306/medquery`.

### 2. MongoDB Setup (via Docker)

MongoDB is used for storing query history and audit logs. Run the following command in your terminal to start a container via Docker Desktop:

```bash
docker run --name medquery-mongo -d -p 27017:27017 mongo:latest

```

## 🚀 Getting Started

### 1. Install Dependencies

Ensure you have Python 3.10+ installed, then run:

```bash
pip install -r requirements.txt

```

### 2. Database Initialization & Seeding

Before starting the server, initialize the MySQL tables and add default users (admin/doctor) by running the seed script:

```bash
python seed_users.py

```

### 3. Run the Server

Start the FastAPI application using Uvicorn:

```bash
uvicorn app.main:app --reload

```

The API documentation will be available at `http://localhost:8000/docs`.

## 📂 Project Structure

* **`app/routers/`**: Contains API endpoints for `query`, `analytics`, `auth`, `notes`, and `history`.
* **`app/database.py`**: Connection logic for both MySQL and MongoDB.
* **`app/auth_utils.py`**: JWT token generation and password hashing.
* **`app/models.py` & `app/schemas.py**`: SQL Alchemy models and Pydantic validation schemas.
