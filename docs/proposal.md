# Raw Proposal Data: ISSR (Task 4)

**AI-Powered Funding Intelligence (FOA Ingestion + Semantic Tagging)**

**Description**
Funding Opportunity Announcements (FOAs) are distributed across many agencies, vary widely in structure, and require significant manual effort to interpret and circulate. This project will build an open-source pipeline that automatically ingests FOAs from public sources, extracts structured fields, and applies ontology-based semantic tags to support institutional research discovery and grant matching.

**Motivation**
Research development teams often lose time and opportunities due to the manual process of finding, parsing, and categorizing FOAs. Automating FOA ingestion and tagging creates structured, queryable funding intelligence that can support investigator discovery, proposal development workflows, and institutional strategy.

**Scope of Work**
1) FOA Ingestion: scraper for Grants.gov + NSF (HTML/PDF formats).
2) Structured Extraction + Normalization: ID, Title, Agency, Open/Close dates, Eligibility, Program description, Award range.
3) Semantic Tagging: Tagging domains, methods, populations using rule-based algorithms, embedding similarity, and optional LLMs.
4) Storage + Export: JSON export, CSV export.
5) Basic Evaluation: Create a small dataset to test baseline tagging accuracy.

**Required Skills**
Strong Python programming skills, Web scraping, NLP tools (spaCy, sentence-transformers), embeddings, APIs, Git/GitHub.

**Screening Task (2-4 Hours)**
Build a minimal script that ingests a single FOA URL, extracts fields into the required schema, applies deterministic rule-based tags. The program must run as: python main.py --url "" --out_dir ./out. Submit main.py, requirements.txt, README.md, out/foa.json, out/foa.csv.

**Mentors**
* Andrya Allen (University of Alabama)
* Dr. Xinyue Ye (University of Alabama)
* Dr. Andrea Underhill (University of Alabama)
