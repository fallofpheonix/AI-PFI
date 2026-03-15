# Submission Guidelines & Constraints: ISSR (Task 4 - FOA Ingestion)

## What to Build (Deliverables)
1. **Working FOA Ingestion + Normalization Pipeline**: Handles HTML/PDF from at least two sources (e.g., Grants.gov, NSF).
2. **Structured FOA Dataset**: JSON + CSV export schemas representing the extracted fields.
3. **Semantic Tagging Module**: Using hybrid approaches (rule-based, embedding similarity, or LLM-assisted) mapped to a defined ontology.
4. **Evaluation Set**: A small ground truth evaluation set with summary metrics (precision/recall/agreement) demonstrating tagging accuracy.

## Screening Task (Required for Application)
Applicants must build a minimal script (2-4 hours) that ingests a single FOA URL, extracts required fields, applies deterministic tags, and outputs files.
- Command execution: `python main.py --url "..." --out_dir ./out`

## What to Submit to Mentor
Applicants should submit the following to **human-ai@cern.ch** with **"Project Title"** in the subject line:
- `main.py`
- `requirements.txt`
- `README.md`
- `out/foa.json`
- `out/foa.csv`
- A current CV or resume.
- **Do NOT contact mentors directly.**

## Constraints
- **Required Stack**: Strong Python skills, `requests`, `BeautifulSoup`, `PyPDF`, `sentence-transformers`.
- **Difficulty**: Medium (175 hours).
