# 🚂 SmartRail: Intelligent TOC Chatbot & Expert System

An advanced AI-driven chatbot designed for a UK Train Operating Company (TOC). This system integrates real-time API data, machine learning for delay prediction, and a rule-based expert system to assist both passengers and operational staff.

---

## 📋 Table of Contents
* [Core Objectives](#-core-objectives)
* [System Architecture](#️-system-architecture)
* [Feature Modules](#-feature-modules)
* [Technical Stack](#-technical-stack)
* [Data & Predictive Modeling](#-data--predictive-modeling)
* [Installation & Setup](#-installation--setup)

---

## ▶️ Code running guidelines
1. Run 1cheapticket.py for getting cheapest ticket data from the Chatbot
2. Run 2knowledgebase.py and 2.1KBwithdelaystationinfo.py, define the path for xlsx files containing training service data from 2022 to 2025 and these scripts use Random Forest training for predicting delayed arrival with enhanced customer support.

## 🎯 Core Objectives

The system addresses three primary personas and use cases:
1. **For Travelers:** Identify the **cheapest available fares** using real-time National Rail data.
2. **For Passengers In-Transit:** Provide AI-powered **arrival time predictions** during delays (Focus: Weymouth to London Waterloo).
3. **For TOC Staff:** A dedicated **Expert System** to provide regulated contingency plans during operational emergencies.

---

## 🏗️ System Architecture

The chatbot is built on a modular **Expert System (ES)** framework as per the following components:

| Component | Description |
| :--- | :--- |
| **User Interface (UI)** | Text-based command-line or web interface for user interaction. |
| **NLP/U Engine** | Processes natural language to extract intent and entities (Dates, Stations, Times). |
| **Reasoning Engine (RE)** | Logic layer that handles multi-turn dialogues and infers answers from the KB. |
| **Knowledge Base (KB)** | Stores Q&As, contingency rules, and station metadata. |
| **Prediction Model (PM)** | Scikit-learn based regression models trained on historical performance data. |
| **Database (DB)** | Saves conversation history, station abbreviations, and historical train data. |

---

## 🚀 Feature Modules

### Task 1: Fare Finder (Cheapest Ticket)
* **Dynamic Dialogue:** Collects departure, destination, and timestamps through conversational flow.
* **API Integration:** Queries the National Rail **Online Journey Planner (OJP)** data feed.
* **Optimization:** Filters results to present only the lowest price with direct booking hyperlinks.
* **Test Scenarios Supported:**
    * *Standard:* Norwich ↔ London (Student trip, July 15–17).
    * *Complex:* Norwich ↔ Oxford (Specific morning/afternoon time constraints).

### Task 2: Customer Service & Delay Prediction
Focuses on the **South Western Railway (Weymouth - London Waterloo)** line.
* **Scenario:** A passenger at Southampton is informed of a 10-minute delay and needs a real-time arrival prediction for London Waterloo.
* **ML Prediction:** Instead of relying on static schedules, the system uses a trained model (e.g., kNN or Random Forest) to predict the actual arrival time based on current delay variables.

### Task 3: Operational Expert System
* **Contingency Handling:** A specialized Knowledge Base containing predefined rules extracted from official TOC regulation documents.
* **Staff Interface:** Provides actionable advice to rail staff for handling emergencies (e.g., track failures, signal issues) through a conversational interface.

---

## 📊 Data & Predictive Modeling

The system utilizes historical rail performance data to improve accuracy over standard timetables.

1. **Preprocessing:** Data is transformed into structured features $X$ (Station, Time of Day, Delay at Entry) and target $y$ (Actual Arrival Time).
2. **Model Selection:** The system evaluates multiple models:
    * $k$-Nearest Neighbors (kNN) Regression
    * Linear/Polynomial Regression
    * Neural Networks
3. **Validation:** Data is partitioned into training and testing subsets. Models are assessed using accuracy measures (MAE/RMSE) before deployment.

---

## 🛠️ Technical Stack

* **Language:** Python 3.x
* **NLP:** `NLTK` / `SpaCy` (Intent classification & Entity recognition)
* **Machine Learning:** `Scikit-learn`, `Pandas`, `NumPy`
* **API Handling:** `Requests` (National Rail RTJP/OJP Data Feed)
* **Database:** `SQLite` or `PostgreSQL`
* **UI:** [CLI / Flask / Streamlit]

---

## 📥 Installation & Setup

1. **Clone the Repository**
   ```bash
   git clone [https://github.com/yourusername/SmartRail-Chatbot.git](https://github.com/IamSudiptoPaul/Chatbot.git)
   cd Chatbot
