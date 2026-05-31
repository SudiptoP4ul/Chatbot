# 🚂 SmartRail: Intelligent TOC Chatbot & Expert System

An advanced, production-ready AI framework designed for UK Train Operating Companies (TOC). This system integrates Retrieval-Augmented Generation (RAG), ensemble machine learning for predictive analytics, and a state-machine driven Expert System to optimize both passenger experience and operational contingency management.

---

<img width="799" height="634" alt="ui" src="https://github.com/user-attachments/assets/bbe013d2-98af-47a7-83b9-57e8d0f58a26" />

<img width="803" height="636" alt="Screenshot 2026-05-28 at 10 39 38 pm" src="https://github.com/user-attachments/assets/e9f5811a-d139-48ff-bd9e-4e17d696dbb5" />

---

## 🎯 System Overview

SmartRail bridges the gap between static regulatory documentation and real-time operational response. By synthesizing **Conversational AI** with **Predictive Analytics**, the framework provides a scalable paradigm for intelligent transportation systems, moving from legacy hard-coded logic to dynamic, LLM-driven intelligence.

---

## 🏗️ Technical Architecture

The framework is built on a modular, multi-agent architecture:

* **LLM-Driven Reasoning:** Uses Retrieval-Augmented Generation (RAG) with ChromaDB for semantic search across regulatory manuals.
* **Deterministic State-Machine:** Manages multi-turn conversational flow to eliminate entropy in critical staff communications.
* **Predictive Engine:** Employs Random Forest Regressors trained on 2022–2025 historical performance data for accurate arrival forecasting.
* **User Interface:** High-performance, cross-platform GUI built with **Flet 0.21.2**, featuring strict station-code validation.

---

## 🚀 Task Modules

### Task 1: Intelligent Fare Finder

* Uses NLP and regex-based extraction to parse travel requirements.
* Integrates real-time National Rail API data to identify the lowest-cost travel options with direct booking support.


<img width="1710" height="1112" alt="cheapest ticket" src="https://github.com/user-attachments/assets/62ab3374-a2d3-4ef9-aa4b-4538f6ce757a" />


### Task 2: Predictive Delay Analytics

* Focuses on line-specific operational volatility (e.g., South Western Railway).
* Implements an ensemble **Random Forest Regressor** to generate data-driven arrival predictions, accounting for historical delay variables rather than relying on static timetables.

<img width="1710" height="1112" alt="delay" src="https://github.com/user-attachments/assets/3e671419-912f-4dbe-b67a-5dd45a371a2f" />


### Task 3: Expert System for Contingency Management

* **RAG Pipeline:** Replaces legacy TF-IDF search with ChromaDB-backed semantic retrieval, allowing the system to interpret complex incident reports.
* **Conversational Diagnostic Partner:** The system handles multi-turn dialogues, dynamically synthesizing contingency protocols from unstructured documentation (PowerPoint/Word).
* **Safety & Escalation:** Proactively provides escalation contacts for incidents outside the ingested knowledge scope.

<img width="1710" height="1112" alt="contingency" src="https://github.com/user-attachments/assets/a5152585-767a-48d0-a942-b13c76d88e34" />


---

## 🛠️ Technical Stack

* **Language:** Python 3.11
* **AI & LLM:** LLaMA / Groq API, ChromaDB (Vector Search), Scikit-learn (Random Forest)
* **GUI:** Flet 0.85.2
* **Data Processing:** pandas, python-docx, python-pptx
* **NLP:** NLTK, difflib (fuzzy matching for station validation)

---

## 📥 Installation & Setup

1. **Clone the Repository**

git clone https://github.com/IamSudiptoPaul/Chatbot.git
cd Chatbot

download requirements.txt to meet all of the criteria:
pip install -r requirements.txt
