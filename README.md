
# TaxTool: Simple Form 1040 PDF Extractor

A lightweight Python tool that gives you a TurboTax-like first pass for a very specific use case:

- Resident Form 1040 only  
- Simple W-2 income  
- Fidelity-style brokerage 1099 income  
- Standard deduction  

It reads your PDFs, extracts key values, and maps them to Form 1040 lines.

---

## What it supports

- W-2 Box 1 wages  
- W-2 Box 2 federal withholding  
- 1099-DIV ordinary dividends (Box 1a)  
- 1099-DIV qualified dividends (Box 1b)  
- 1099-DIV tax-exempt interest dividends  
- 1099-B short-term and long-term gain summaries  
- Basic refund / amount owed logic (when taxable income is zero)  

---

## What it does not support yet

- Form 1040-NR  
- Itemized deductions  
- Dependents / tax credits  
- Education credits  
- IRA / HSA adjustments  
- Self-employment income  
- State returns  
- Full federal tax calculation for nonzero taxable income  
- Form 8949 detailed transaction breakdown  
- E-filing  

---

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install pypdf pdfplumber
````

---

## File setup

Place your PDFs anywhere and pass their paths via CLI.

Example project structure:

```
TaxTool/
- tax1040_simple.py
- 2025 W2.pdf
- 2025 Fidelity 1099.pdf
- other_1099.pdf
```

Notes:

* File names do NOT need to match exactly
* You can use full paths or relative paths
* Spaces in file names are supported (use quotes)

---

## Run

```bash
python tax1040_simple.py \
  --resident-return \
  --tax-year 2025 \
  --w2 "/path/to/2025 W2.pdf" \
  --brokerage-1099 "/path/to/2025 Fidelity 1099.pdf" \
  --brokerage-1099 "/path/to/other 1099.pdf" \
  --output-json tax_summary.json \
  --output-report tax_report.md
```

---

## Windows (PowerShell)

### Activate environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

---

### Install

```powershell
pip install pypdf pdfplumber
```

---

### Run (single line)

```powershell
python .\tax1040_simple.py --resident-return --tax-year 2025 --w2 ".\2025 W2.pdf" --brokerage-1099 ".\2025 Fidelity 1099.pdf" --brokerage-1099 ".\other_1099.pdf" --output-json ".\tax_summary.json" --output-report ".\tax_report.md"
```

---

## Output

The tool generates:

* `tax_summary.json`
* `tax_report.md`

---

## Sample output

### tax_summary.json

```json
{
  "wages": 9330,
  "ordinary_dividends": 13,
  "qualified_dividends": 10,
  "capital_gain": 10,
  "total_income": 9354,
  "standard_deduction": 15750,
  "taxable_income": 0,
  "federal_tax": 0,
  "federal_withholding": 1146,
  "refund": 1146,
  "amount_owed": 0
}
```

---

### tax_report.md (simplified)

```
W-2
- Wages (Box 1): 9330
- Federal withholding (Box 2): 1146

1099-DIV
- Ordinary dividends: 13
- Qualified dividends: 10

1099-B
- Capital gain (short-term + long-term): 10

Form 1040 summary
- Total income: 9354
- Standard deduction: 15750
- Taxable income: 0
- Federal tax: 0
- Refund: 1146
```

---

## How to interpret

* Wages → W-2 Box 1
* Withholding → W-2 Box 2
* Dividends → 1099-DIV
* Capital gains → 1099-B

The tool combines these values and applies the standard deduction.

In this example:

* Taxable income becomes 0
* All withholding is refunded

---

## Mapping to Form 1040

### Income

| Source              | Document Field  | Form 1040 Line |
| ------------------- | --------------- | -------------- |
| Wages               | W-2 Box 1       | Line 1a        |
| Ordinary dividends  | 1099-DIV Box 1a | Line 3b        |
| Qualified dividends | 1099-DIV Box 1b | Line 3a        |
| Capital gains       | 1099-B summary  | Line 7         |

---

### Deductions

| Component          | Description           | Line    |
| ------------------ | --------------------- | ------- |
| Standard deduction | Applied automatically | Line 12 |

---

### Tax

| Component      | Description             | Line    |
| -------------- | ----------------------- | ------- |
| Taxable income | Income - deductions     | Line 15 |
| Federal tax    | (Not fully implemented) | Line 16 |

---

### Payments

| Component        | Source     | Line     |
| ---------------- | ---------- | -------- |
| W-2 withholding  | W-2 Box 2  | Line 25a |
| 1099 withholding | 1099 forms | Line 25b |
| Refund           | Calculated | Line 34  |
| Amount owed      | Calculated | Line 37  |

---

## Schedule D and Form 8949 handling

### Schedule D (capital gains summary)

The tool generates a simplified Schedule D using aggregated values from 1099-B statements.

Mapping:

| Source | Description | Schedule D Line |
|--------|------------|-----------------|
| Short-term proceeds and cost basis | Covered securities (basis reported) | Part I, Line 1a |
| Net short-term gain/loss | Aggregated short-term result | Line 7 |
| Long-term proceeds and cost basis | Covered securities (basis reported) | Part II, Line 8a |
| Net long-term gain/loss | Aggregated long-term result | Line 15 |
| Total capital gain/loss | Combined net gain | Line 16 |

The tool currently assumes:

- Transactions are covered (basis reported to the IRS)  
- No adjustments are required (e.g., wash sales, disallowed losses)  
- Summary totals from 1099-B can be directly reported on Line 1a / Line 8a  

---

### Form 8949 (not implemented)

Form 8949 is not generated by this tool.

This means:

- Individual transactions are not listed  
- Adjustment codes are not handled  
- Wash sales and other corrections are not applied  
- Only summary totals are used  

You may need to manually complete Form 8949 if your brokerage statement includes:

- Noncovered securities  
- Wash sale adjustments  
- Missing or incorrect cost basis  
- Multiple adjustment categories  

---

### Important note

This tool is designed for simple capital gains scenarios where:

- 1099-B provides clean summary totals  
- No adjustments are required  
- Values can be directly mapped to Schedule D  

Always verify results against your brokerage statement and final tax software before filing.

---

## Notes

* Values are rounded to whole dollars per IRS rules
* Brokerage statements marked as “not filed with the IRS” are still included
* Schedule D mapping assumes covered transactions without adjustments
* This is a simplified estimator, not filing software

---

## Recommended next upgrades

1. Add real federal tax calculation (brackets + qualified dividends)
2. Implement full Form 8949 transaction mapping
3. Support more broker formats beyond Fidelity
4. Add a Streamlit UI
5. Add unit tests with redacted PDFs

---

## Safety note

Use this as a calculator and organizer, not as final filing software.
Always verify against your source documents and final return.

---

## How to file your taxes

This tool prepares your data but does not submit returns.

### Option 1: E-file (recommended)

Use:

* FreeTaxUSA
* TurboTax

Steps:

* Enter W-2 data
* Enter 1099-DIV
* Enter 1099-B
* Review and submit

---

### Option 2: Manual filing

* Download Form 1040
* Fill using generated values
* Print and mail

---

## Cost comparison

Typical costs:

* Tax consultant: $150–$500+
* TurboTax: $100+
* FreeTaxUSA:

  * Federal: $0
  * State: ~$15

Using this tool:

* Data prep: $0
* Filing: ~$0–$15

---

## Summary

This tool helps you:

* Understand your tax data
* Verify numbers before filing
* Reduce reliance on expensive tax prep services
