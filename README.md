# 🚦 Traffic Management System

A real-time traffic monitoring and analysis system built using Computer Vision, FastAPI, and a simulation pipeline. This project is designed as a collaborative minor project with a modular architecture.

---

## 📌 Project Overview

The goal of this project is to:

* Simulate real-world traffic data
* Process and analyze traffic patterns
* Provide insights via APIs
* Visualize data through a frontend dashboard

This system mimics how smart cities manage traffic using AI and data analytics.

---

## 🧠 Architecture

```
Simulator → Backend API → Database → Frontend Dashboard
```

### Components:

* **Simulator (Student 1)**

  * Generates synthetic traffic data
  * Sends data to backend via ingestion pipeline

* **Backend (Student 2)**

  * FastAPI server
  * Stores and processes incoming traffic data
  * Performs analysis

* **Frontend (Student 3)**

  * Displays traffic insights visually
  * Fetches data from backend APIs

---

## 📁 Project Structure

```
traffic-management-system/
├── JSON_CONTRACT.md
├── README.md
├── backend/
├── simulator/
├── frontend/
└── tests/
```

---

## ⚙️ Tech Stack

* **Backend:** FastAPI, Python
* **Simulator:** Python
* **Frontend:** React.js
* **Database:** PostgreSQL / SQLite
* **Testing:** Pytest

---

## 🚀 Getting Started

### 1. Clone Repository

```bash
git clone https://github.com/your-username/traffic-management-system.git
cd traffic-management-system
```

---

### 2. Setup Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs at:

```
http://127.0.0.1:8000
```

---

### 3. Setup Simulator

```bash
cd simulator
pip install -r requirements.txt
bash start.sh
```

This will start sending simulated traffic data to backend.

---

### 4. Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

```
http://localhost:5173
```

---

## 🔌 API Endpoints (Basic)

| Method | Endpoint  | Description          |
| ------ | --------- | -------------------- |
| POST   | /ingest   | Receive traffic data |
| GET    | /traffic  | Get all traffic data |
| GET    | /analysis | Get traffic insights |

---

## 🧪 Running Tests

```bash
cd tests
pytest
```

---

## 👥 Team Responsibilities

| Student   | Responsibility             |
| --------- | -------------------------- |
| Student 1 | Simulator + Data Ingestion |
| Student 2 | Backend + Analysis         |
| Student 3 | Frontend + Testing         |

---

## 📌 Future Improvements

* Real CV-based detection (YOLO / OpenCV)
* Live camera integration
* Traffic signal optimization
* ML-based congestion prediction

---

## 🤝 Contribution Guidelines

* Follow JSON contract strictly
* Use clear commit messages
* Test before pushing code

---

## 📄 License

This project is for academic purposes.
