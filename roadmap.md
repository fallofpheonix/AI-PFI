# Architecture & Roadmap Plan: ISSR (Task 4 - FOA Ingestion)

## 1. Roadmap
- **Phase 1: Ingestion & Normalization**
  - Use `requests`/`BeautifulSoup` to scrape HTML sources (Grants.gov).
  - Use `PyPDF2`/`PDFMiner` to parse NSF PDF forms.
  - Implement regex and rule-based logic to extract specific unstructured strings into the ISO-standard schema (Dates, Amounts).
- **Phase 2: Semantic Ontology Mapping**
  - Define the domain vocabulary ontology mapping.
  - Utilize `sentence-transformers` to embed the extracted unstructured text descriptions and calculate cosine similarity against ontology anchors.
- **Phase 3: Storage & CLI Packaging**
  - Implement JSON/CSV output serialization logic.
  - Package the scraper via a robust `argparse` CLI (`python main.py --url...`).
- **Phase 4: Evaluation Metrics (Stretch: Search)**
  - Establish a golden set of 50-100 manually annotated FOAs to compute F1/Recall/Precision scores for the automated semantic tagger.
  - (Stretch) Integrate a vector DB index (`FAISS` or `Chroma`) to allow semantic search queries across the extracted database.

## 2. Architecture Plan
- **Spider Layer**: A modular Python class meant to be subclassed per agency (e.g., `GrantsGovSpider`, `NSFSpider`) allowing highly specific HTML/PDF parsing logic.
- **NLP Tagging Layer**: 
  - Module 1: Deterministic dictionary mapping (Rule-based).
  - Module 2: Embedding Similarity matcher (HuggingFace transformers) falling back to zero-shot LLM (Gemini API) for highly ambiguous descriptions.
- **Data Persistence**: Local JSON/CSV serialization, abstracted behind a DAO interface for future integration into Postgres/MongoDB.

## 3. Changes Needed
- Ensure the screening task `main.py` is capable of handling HTTP timeouts and Malformed HTML without throwing fatal unhandled exceptions.

## 4. Current Problems
- PDF parsing from federal agencies is notoriously unstable due to non-standardized OCR embeds and unpredictable table layouts within the PDFs.

## 5. Problems It Can Cause
- **Hallucinated Extractions**: An LLM-based tagger might hallucinate Award Amounts or misread tricky Open/Close dates (e.g., reading "2027" as "2026"), which would severely impact institutional grant application pipelines.

## 6. Future Work
- Connecting the output schema directly to an active directory of university professors/investigators, automatically emailing matching FOAs to investigators based on their previous publication embeddings.
