# Mikha Denagil Spiritual Society Management System

A comprehensive management system built for the **Mikha Denagil Spiritual Society** to handle member registration in bulk, attendance tracking, and upcoming modules like library, MEWACO, mobile-based attendance, and more.

---

## ✅ Current Features Implemented

- 🔁 **Mass Member Upload** via Excel or CSV
- 📋 **Attendance Management System** with filtering and tracking
- 🧾 **Attendance Reports** exportable and categorized by section or medebe
- 🔒 **User Authentication** using JWT or session-based login
- 📁 **Member Management**: Add, update, delete member records
- 🔍 **Search & Filter** by name, ID, or group
- 📊 **Dashboard with Attendance Charts**

---

## 🔮 Upcoming Features

- 📚 **Library Management**
- 📆 **Holiday Selector and Calendar**
- 📱 **Mobile App for Attendance (Android/iOS)**
- 💧 **MEWACO (Contribution) Management**
- 🏢 **Section & Medebe Management**

---

## 🖥️ Screenshots

> 📌 Add actual screenshots in `/screenshots/` and replace the image links below

| Dashboard | Attendance Form | Member Registartion |
|-----------|------------------|----------------|
| ![Dashboard](dasbord.png) | ![Attendance](attendance.png) | ![Upload](registartion.png) |

---

## 🛠️ Technologies Used

- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap
- **Backend**: Python (Flask Framework)
- **Database**: Oracle Database
- **Authentication**: JWT or Flask session-based login
- **Charts & Visualization**: Chart.js or ApexCharts

---

## 🚀 Installation Guide

### Prerequisites

- Python 3.8+
- Oracle Client (configured and accessible)
- Git
- pipenv or virtualenv (recommended)

### Step-by-Step Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/Mikha_Denagil.git
   cd Mikha_Denagil

Set Up Virtual Environment

bash
Copy
Edit
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
Install Dependencies

bash
Copy
Edit
pip install -r requirements.txt
Set Up Oracle DB Connection

Update your Flask config.py or .env file with:

env
Copy
Edit
ORACLE_USER=your_db_user
ORACLE_PASSWORD=your_db_password
ORACLE_DSN=localhost:1522/orcl2
SECRET_KEY=your_secret_key
Run the Application

bash
Copy
Edit
flask db upgrade   # If using Alembic for migrations
flask run
Access the System

Open your browser and go to: http://127.0.0.1:5000/

📂 Project Structure
arduino
Copy
Edit
mikha-denagil-society-system/
├── app/
│   ├── templates/
│   ├── static/
│   ├── routes/
│   ├── models/
│   └── __init__.py
├── screenshots/
├── config.py
├── requirements.txt
├── run.py
└── README.md
