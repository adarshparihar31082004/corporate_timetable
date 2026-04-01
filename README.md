# corporate_timetable
Corporate Weekly Planner built with FastAPI that allows teams to create, save, and export structured weekly schedules as professional PDF planners with logo branding, notes, and database persistence.
# Corporate Weekly Planner

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/status-active-success)

A **corporate-grade weekly planning system** built with **FastAPI, SQLAlchemy, and ReportLab** that allows organizations to design structured weekly schedules and export them as professional PDF planners.

---

# Overview

Corporate Weekly Planner helps teams and departments create structured weekly schedules with metadata, logos, notes, and printable layouts.

The application generates **high-quality branded PDF planners** suitable for corporate operations, meetings, or team planning.

---

# Key Features

### Planner Management
- Create structured weekly schedules
- Add organization, department, and team information
- Add prepared-by metadata
- Save planners to database
- Load previously created planners

### Planner Editor
- Dynamic task rows
- Break rows for lunch / pauses
- Multi-line task entries
- Week range support
- Notes / remarks section

### Branding Support
- Upload organization logo
- Generate branded planner PDFs
- Confidential internal document banner

### Export
- Export planner to **professional landscape PDF**
- Print-ready layout
- Corporate table styling

---

# Tech Stack

### Backend
FastAPI  
SQLAlchemy  
Pydantic

### Frontend
HTML  
CSS  
JavaScript

### Database
SQLite

### PDF Engine
ReportLab

---

# Architecture


Client (Browser)
│
│ HTTP
▼
FastAPI Backend
│
├── Planner API
├── Logo Upload API
├── PDF Generator
│
▼
SQLite Database


---

# Project Structure


corporate-weekly-planner
│
├── main.py
├── database.py
├── models.py
├── planner.db
│
├── templates
│ └── index.html
│
├── static
│ └── uploads
│
├── README.md
└── requirements.txt


---

# Installation

1 Clone repository

```bash
git clone https://github.com/adarshparihar31082004/corporate-weekly-planner.git
cd corporate-weekly-planner
2 Install dependencies
pip install -r requirements.txt
3 Run application
uvicorn main:app --reload
4 Open in browser
http://127.0.0.1:8000
API Endpoints
Endpoint	Method	Description
/	GET	Planner UI
/upload-logo	POST	Upload company logo
/save-planner	POST	Save planner to database
/load-planner/{id}	GET	Load saved planner
/generate-pdf	POST	Generate planner PDF
