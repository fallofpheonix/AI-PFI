# AI-PFI System Architecture Roadmap
**System Classification: DEVELOPMENT**

Following a comprehensive 11-Phase Audit and live-repair session, the AI-PFI system architecture is definitively rated as a **DEVELOPMENT** candidate. 

While the underlying NLP extraction algorithms and basic tagging workflows are structurally clean and functional, the system entirely lacks the infrastructure required for production scaling, such as a database layer, a web frontend, active CI/CD, and asynchronous APIs.

The following Priority Repair Roadmap outlines the necessary engineering steps required to transition this system to an enterprise-grade `PRODUCTION READY` state.

---

## 🔴 CRITICAL FIXES (Pre-Requisites for Staging)
These items block the system from being deployed concurrently or exposed to end-users.

1. **Transactional Database Layer**
   - **Context**: The `FOAStore` relies on naive JSONL file rewrites (`self._flush_snapshot()`) on every `.upsert()`.
   - **Action**: Replace `FOAStore` with a real relational database (e.g., **PostgreSQL** with `JSONB` or **SQLite** for staging) via an ORM like SQLAlchemy to enforce ACID compliance and prevent data corruption during parallel processing.
2. **Build System & CI/CD Validation**
   - **Context**: `requirements.txt` lacks hashed versions, and there is no automated testing hook.
   - **Action**: Migrate dependencies to `Poetry` or `pip-tools`. Implement a `.github/workflows/ci.yml` file to automatically run `pytest` and `flake8` on PRs. Create a `Dockerfile` to standardize execution environments.
3. **ML Pipeline Dataset Engineering**
   - **Context**: The evaluation dataset is mocked with 8 static records inside the `metrics.py` file.
   - **Action**: Construct a dedicated `data/eval.jsonl` representing at least 250 diverse FOAs. Separate Train/Val pipelines for metric evaluation.

## 🟠 HIGH IMPACT IMPROVEMENTS (To Reach Production)
These items deliver the most direct business value to scaling operations.

1. **Web API & Frontend Server**
   - **Context**: Operation is locked within an IO-bound CLI script (`main.py`).
   - **Action**: Implement a **FastAPI** backend to expose endpoints (`/api/v1/foa/ingest`, `/api/v1/foa/search`). Build a lightweight Web Frontend (e.g., **Next.js** or **Streamlit**) that consumes this API to allow end-users to search and filter FOA tags visually.
2. **Domain-Specific Fine Tuning**
   - **Context**: Uses baseline `sentence-transformers/all-MiniLM-L6-v2` with no domain awareness of federal grants.
   - **Action**: Fine-tune contrastive embeddings on government terminology, or migrate to `PubMedBERT` or MS-MARCO derivatives to significantly boost retrieval recall.

## 🟡 MEDIUM IMPACT OPTIMIZATIONS
These items enhance reliability and lower operational costs.

1. **Robust LLM Parsing & Retry Architectures**
   - **Context**: The `LLMTagger` relies on brittle Regex stripping for JSON generation without structural enforcement.
   - **Action**: Wrap Anthropic and OpenAI calls in the `instructor` or `pydantic` libraries to force guaranteed JSON schemas, automatically retrying on formatting or HTTP timeout failures.
2. **Rate Limiting & Queue Orchestration**
   - **Context**: The newly added `ThreadPoolExecutor` indiscriminately requests URLs to Grants.gov.
   - **Action**: Implement an asynchronous Task Queue (e.g., **Celery** + Redis) with explicit rate limiters to avoid being blacklisted by scraping targets.

## 🟢 LOW PRIORITY REFACTORS
1. **Systematic Pre-Commit Hooks**
   - Enforce `black`, `flake8`, and `isort` statically using `.pre-commit-config.yaml`.
