
## TaxTool: A Local PDF Tax Data Extractor and Mapper

A lightweight Python tool to extract, understand, and map tax data from W-2 and 1099 PDFs to Form 1040.

## Design and architecture

The tool is designed as a small local pipeline that converts raw tax documents into structured tax values and a simple Form 1040 summary.

### High-level flow

1. Read PDF files
2. Extract text from each document
3. Detect document type
4. Parse supported tax fields
5. Aggregate values across documents
6. Map values to Form 1040 lines
7. Generate output reports

### Core components

#### 1. PDF reader

Responsible for reading text from uploaded PDF files using local Python libraries.

Purpose:
- open W-2 and 1099 PDFs
- extract readable text
- fall back across libraries if one parser fails

#### 2. Document parser

Parses each document type separately.

Supported parsers:
- W-2 parser
- 1099-DIV parser
- 1099-B parser

Purpose:
- identify relevant boxes or summary values
- normalize extracted values into structured fields

Example normalized fields:
- wages
- federal_withholding
- ordinary_dividends
- qualified_dividends
- short_term_gain
- long_term_gain

#### 3. Aggregation layer

Combines values from multiple documents into one tax summary.

Purpose:
- sum values across multiple W-2s or 1099s
- ignore unsupported or non-material files when applicable
- prepare a single tax data object for calculation

#### 4. Tax calculation layer

Applies simple resident Form 1040 logic.

Purpose:
- compute total income
- apply standard deduction
- estimate taxable income
- estimate refund or amount owed

Current scope:
- simple resident 1040 only
- standard deduction only
- basic zero-tax / refund scenarios

#### 5. Output generator

Writes results into user-friendly output files.

Outputs:
- `tax_summary.json`
- `tax_report.md`

Purpose:
- provide structured machine-readable output
- provide a human-readable summary for review and filing

---

### Why the architecture is useful

This separation makes the tool easier to extend.

For example:
- new broker formats can be added as new parsers
- additional tax rules can be added in the calculation layer
- a web UI can be added without changing parsing logic
- output formats can be expanded independently

---

### Future architecture improvements

Potential extensions:
- plugin-based parser system for multiple brokers
- support for Form 1040-NR
- Streamlit or web UI for drag-and-drop uploads
- validation layer for missing or suspicious values
- PDF form generation for draft tax returns
- support for additional schedules and tax credits