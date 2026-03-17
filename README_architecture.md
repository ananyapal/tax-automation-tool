## Design and architecture

The tool is designed as a local data processing pipeline that converts raw tax documents into structured tax values and a simplified Form 1040 summary.

---

### High-level flow

1. Read PDF files  
2. Extract text from each document  
3. Assign document type via CLI input  
4. Parse supported tax fields  
5. Aggregate values across documents  
6. Map values to Form 1040 lines  
7. Generate output reports  

---

### Core components

#### 1. PDF reader

Responsible for reading text from PDF files using local Python libraries.

Purpose:
- open W-2 and 1099 PDFs  
- extract readable text  
- fall back across libraries if one parser fails  

---

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

---

#### 3. Data model layer

Defines structured representations for parsed data.

Purpose:
- store normalized values from different document types  
- provide a consistent interface for aggregation and calculation  

Examples:
- W2Data  
- Brokerage1099Data  
- Form1040SimpleResult  

---

#### 4. Aggregation layer

Combines values from multiple documents into a single tax summary.

Purpose:
- sum values across multiple W-2s or 1099s  
- combine all provided documents into one unified dataset  
- flag unusual cases (e.g., statements marked as not filed with IRS)  

---

#### 5. Tax calculation layer

Applies simplified resident Form 1040 logic.

Purpose:
- compute total income  
- apply standard deduction  
- estimate taxable income  
- estimate refund or amount owed (accurate when taxable income is zero)  

Current scope:
- simple resident 1040 only  
- standard deduction only  
- no full tax bracket calculation  

---

#### 6. Output generator

Writes results into user-friendly output files.

Outputs:
- `tax_summary.json`  
- `tax_report.md`  

Purpose:
- provide structured machine-readable output  
- provide a human-readable summary for review and filing  

---

### Why the architecture is useful

This separation makes the tool easy to extend.

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