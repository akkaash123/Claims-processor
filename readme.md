# 🛡️ Plum AI Claims Processor

A Neuro-Symbolic, Fail-Fast AI pipeline for automated health insurance claim adjudication. Built with FastAPI, LangGraph, Google Gemini 2.5 Flash, and Next.js.

This system replaces manual claims processing by combining the semantic reasoning of Large Language Models (LLMs) with the strict, deterministic accuracy of Actuarial Mathematics. 

## ✨ Key Architectural Features

* **Fail-Fast LangGraph DAG:** A directed acyclic graph architecture that routes claims through multiple validation nodes (Bouncer → Fraud → Extractor → Actuarial Math). It catches simple errors (missing documents, name mismatches) in milliseconds, bypassing expensive AI compute.
* **Neuro-Symbolic AI:** Gemini 2.5 Flash is strictly bound to Pydantic schemas (`structured_output`). The AI handles semantic translations (e.g., expanding "HTN" to "Hypertension", reading blurry text), while a deterministic Python engine handles all financial math and policy limit capping.
* **Zero-Hardcoding Policy Engine:** 100% of the actuarial rules, sub-limits, network discounts, and waiting periods are loaded dynamically from `policy_terms.json`.
* **Smart UI Routing:** A 5-step React wizard that parses API `422` and validation errors to dynamically slide the user back to the exact step where a document failed AI ingestion.
* **Graceful Degradation:** If the LLM hits a rate limit or API failure, the system automatically lowers the confidence score and routes the claim to `MANUAL_REVIEW` instead of throwing a 500 Server Error.

## 🛠️ Tech Stack

* **Backend:** Python 3.10+, FastAPI, LangGraph, LangChain, SQLite (Long-term fraud memory)
* **AI Model:** Google `gemini-2.5-flash`
* **Frontend:** Next.js 14, React, Tailwind CSS, Lucide Icons

## 🚀 Getting Started

### Prerequisites

* Node.js (v18+)
* Python (3.10+)
* A Google Gemini API Key

### 1. Backend Setup (FastAPI)

Navigate to the root directory and set up your Python environment:

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn python-multipart pydantic langchain-google-genai langgraph python-dotenv

# Set your API Key
echo "GOOGLE_API_KEY=your_api_key_here" > .env

# Start the server
uvicorn main:app --reload --port 8000
The backend will be running at http://127.0.0.1:8000

2. Frontend Setup (Next.js)
Open a new terminal window and navigate to the frontend directory:

Bash


cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
The frontend will be running at http://localhost:3000

📁 Project Structure
Plaintext


plum-claims-processor/
├── main.py                     # FastAPI application & endpoints
├── data/
│   └── policy_terms.json       # Dynamic insurance policy configuration
├── app/
│   └── core/
│       ├── schemas.py          # Pydantic models for Neuro-Symbolic contract
│       ├── agents.py           # Gemini AI extraction prompts & logic
│       ├── policy_math.py      # Deterministic actuarial engine
│       └── engine.py           # LangGraph DAG state machine
└── frontend/
    └── app/
        └── page.tsx            # Next.js 5-Step Claim Wizard UI
🧪 Testing
The repository includes a comprehensive test_cases.json suite designed to test fraud triggers, limit capping, category mismatches, and AI hallucination handling. You can generate the mock documents for these tests using the included generate_mocks.py Pillow script.