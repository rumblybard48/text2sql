# Text-to-SQL Engine

An enterprise-ready, modular Text-to-SQL pipeline designed to translate natural language questions into accurate, secure SQL queries. The system features schema extraction, intelligent filtering, verification guardrails, query scoring, an evaluation benchmark suite, and an interactive frontend.

---

## Key Features

- **Schema Extraction & Intelligent Filtering:** Dynamically extracts database metadata and narrows down relevant tables/columns to optimize prompt context.
- **SQL Generation & Candidate Scoring:** Leverages language models to craft targeted queries, scoring candidate outputs for precision.
- **Guardrails & Execution Sandbox:** Pre-execution verification and safety checks to prevent malicious operations, syntax errors, and destructive statements.
- **Evaluation Suite:** Benchmark pipeline with a golden dataset (`evals/golden_dataset.json`) and automated scoring scripts (`evals/run_evals.py`).
- **Interactive UI & Containerization:** Built-in web frontend and full Docker/Docker Compose support for simple local deployment.

---

## Project Structure

```text
text2sql/
├── app/
│   ├── main.py                  # API / core orchestration entry point
│   └── services/
│       ├── schema_extractor.py  # Database schema reflection & inspection
│       ├── schema_filter.py     # Relevant table/column selection
│       ├── sql_generator.py     # Prompting & LLM query generation
│       ├── verifier.py          # Syntax & semantic verification
│       ├── guardrails.py        # Safety & injection prevention checks
│       ├── scoring.py           # Ranking & scoring candidate queries
│       └── executor.py          # Secure SQL execution engine
├── evals/
│   ├── golden_dataset.json      # Ground-truth evaluation dataset
│   └── run_evals.py             # Evaluation benchmark runner
├── frontend/
│   └── app.py                   # Interactive user interface
├── Dockerfile                   # Application container definition
├── docker-compose.yml           # Multi-container orchestration
├── requirements.txt             # Python dependencies
├── test_db.db                   # Sample/testing database
└── test.py                      # Integration and unit tests
```

---

## Architecture Flow

```
[ Natural Language Query ]
            │
            ▼
┌─────────────────────────┐
│ Schema Extractor/Filter │ ◄── [ Target Database ]
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│      SQL Generator      │ (LLM Engine)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Guardrails & Verifier  │ (Safety, Syntax & Rule Checks)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│     Query Executor      │ ──► [ Database Execution ]
└───────────┬─────────────┘
            │
            ▼
   [ Structured Results ]
```

---

## Getting Started

### Prerequisites

- Python 3.10+ (or Python 3.11/3.14)
- Docker & Docker Compose (optional, for containerized run)

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/text2sql.git
   cd text2sql
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the backend:**
   ```bash
   python -m app.main
   ```

5. **Run the frontend:**
   ```bash
   python frontend/app.py
   ```

---

## Running with Docker

You can spin up the application stack using Docker Compose:

```bash
docker-compose up --build
```

---

## Running Evaluations

To run the automated benchmark against the golden evaluation set:

```bash
python evals/run_evals.py
```

To run test suites:
```bash
python test.py
```

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
