# 🛡️ ArchGuard: AI PR Risk Analyzer

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai&logoColor=white)
![Pinecone](https://img.shields.io/badge/Pinecone-Vector_DB-000000?logo=pinecone)

**ArchGuard** is an intelligent, cognitive code safety pipeline. It moves beyond standard syntax linting to detect structural anti-patterns, calculate the potential blast radius of a Pull Request, and orchestrate automated, programmatic rollbacks to protect production environments.


![Uploading Gemini_Generated_Image_ia87ldia87ldia87.png…]()


**Live Demo:** [arch-guard-hackathon.vercel.app](https://arch-guard-hackathon.vercel.app)

---

## The Problem
Standard CI/CD pipelines and static analyzers catch syntax errors, but they miss **contextual architectural drift**. A missing HTTP timeout or a lack of connection pooling isn't a syntax error—it's a cascading failure waiting to happen. 

## The ArchGuard Solution (The 4-Layer Pipeline)
ArchGuard intercepts Pull Requests and passes them through a 4-layer cognitive analysis pipeline:

1. **L1: Static AST Engine** * Traverses Abstract Syntax Trees (AST) to detect raw structural flaws (e.g., blocking calls inside loops, missing circuit breakers, bare exceptions) without needing to execute the code.
2. **L2: Contextual Memory (RAG)**
   * Utilizes **Pinecone** to cross-reference L1 findings against the *ArchGuard Outage & Incident Corpus (AOIC)*—a dataset of historical DevOps post-mortems—to determine real-world blast radius.
3. **L3: Cognitive Synthesis (LangGraph)**
   * Manages a **Human-in-the-Loop (HITL)** flow. The AI pauses to ask developers for critical business context (e.g., target RPS, strict SLOs) to eliminate false positives and calculate an accurate Risk Score.
4. **L4: Action & Remediation Engine**
   * Automatically executes a **Git Tree Replacement Revert** via the GitHub REST API. It isolates the last known stable commit and orchestrates a clean, conflict-free PR to contain critical vulnerabilities before deployment.

---

## Tech Stack

* **Backend & API:** FastAPI, Uvicorn, Python `ast` module.
* **AI & Orchestration:** OpenAI (GPT-4o), LangGraph, LangChain.
* **Vector Database:** Pinecone.
* **Integrations:** GitHub REST API (Server-Side PAT Authentication).
* **Frontend:** React, Vite, Tailwind CSS (Hosted on Vercel).

---

## Local Development Setup

Follow these steps to run the ArchGuard backend locally.

### 1. Clone the repository
```bash
git clone [https://github.com/UjwalDwivedi/archguard.git](https://github.com/UjwalDwivedi/archguard.git)
cd archguard
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
Create a .env file in the root directory and add the following keys:
GITHUB_TOKEN=your_github_personal_access_token
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=archguard-index

Because the architecture is modularized, start the server pointing to the app directory:
uvicorn app.main:app --reload
```

---

## Core API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/analyze-pr` | `POST` | Fetches PR diffs via GitHub API, runs AST parsing, and initializes the LangGraph AI state. |
| `/submit-answers` | `POST` | Resumes the AI pipeline with developer context (HITL) to calculate the final Risk Score. |
| `/enforce-rollback` | `POST` | Triggers the automated Git Tree reversion and creates a rollback PR. |

---

Contributor :
Ujwal Dwivedi,
Rudri Bosamia.
