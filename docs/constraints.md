# Constraints and Restrictions: ISSR - task4

## Technical Constraints

### Required Stack

The stated stack for screening/full work includes:

```
Python
requests
BeautifulSoup
PyPDF
sentence-transformers
```

### Input Constraints

The pipeline must handle at least:

```
HTML FOA pages
PDF FOA documents
mixed formatting across agencies
```

### Output Constraints

The screening script must produce:

```
out/foa.json
out/foa.csv
```

At minimum, extracted records should preserve deterministic normalized fields such as:

```
title
agency
open_date
close_date
award_range
eligibility
tags
source_url
```

### Robustness Constraints

The ingestion path must not crash on:

```
HTTP timeouts
missing fields
malformed HTML
partially unreadable PDFs
```

Failures should degrade into explicit missing-field outputs and clear status reporting.

### Evaluation Constraints

Semantic tagging must be testable against a small manually reviewed set. Deterministic rule-based baselines should exist before any embedding or LLM-assisted tagging is introduced.
