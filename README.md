# CKIN — Campus Knowledge and Innovation Network

CKIN is an intelligent web-based platform designed for academic student project discovery, duplicate detection using NLP, machine-learning teammate matching, collaboration tracking, and faculty review.

---

## Quick Setup & Execution Guide (Windows & VS Code)

### Step 1: Open Terminal & Navigate to Project Directory
```powershell
cd C:\Users\hp\.gemini\antigravity-ide\scratch\CKIN
```

### Step 2: Initialize Database and Seed Demo Data
```powershell
python init_db.py
python seed_demo_data.py
```

### Step 3: Train Machine Learning Recommendation Models
```powershell
python train_model.py
```

### Step 4: Run Automated Test Suite
```powershell
python run_tests.py
```

### Step 5: Start the Flask Application
```powershell
python app.py
```

Then open your browser and navigate to:
`http://localhost:5000` or `http://127.0.0.1:5000`

---

## 🔑 Demo Account Credentials

For quick evaluation during project review, use these pre-seeded demo accounts (all with password `password123`):

| Role | Email | Password | Features / View |
| :--- | :--- | :--- | :--- |
| **Student** | `student@ckin.local` | `password123` | Submit projects, AI Recommendations, Teammate Matching, What-If Simulator, Invitations |
| **Faculty** | `faculty@ckin.local` | `password123` | Faculty Review Queue, NLP Similarity Signals, Approve/Reject Submissions |
| **Admin** | `admin@ckin.local` | `password123` | System Monitoring, Account Listings, Activity Logs & Metrics |

---

## 🛠️ Architecture & Core Components

- **Backend Framework**: Python 3.11+ with Flask
- **Database Layer**: SQLite 3 with normalized tables (users, profiles, projects, members, join_requests, team_invitations, tasks, notifications, activity_logs)
- **NLP Duplicate Engine**: `TfidfVectorizer` + Cosine Similarity (`src/similarity_engine.py`)
- **ML Recommendation Engine**: Logistic Regression / Random Forest / Gradient Boosting with feature engineering (`src/feature_engineering.py`, `src/train_model.py`, `src/recommendation_engine.py`)
- **Teammate Matching**: Multi-criteria student scoring (`src/team_recommender.py`)
- **Frontend**: HTML5, Vanilla CSS3 (Custom Dark Theme Aesthetic), Bootstrap 5 CDN, JavaScript AJAX
