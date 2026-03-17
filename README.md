# Simple Tax Automation Starter

This is a small local Python tool that gives you a TurboTax-like first pass for a very specific case:

- resident Form 1040 only
- simple W-2 income
- Fidelity-style brokerage 1099 income
- standard deduction

It reads your PDFs, extracts key values, and maps them to the main Form 1040 lines.

---

## What it supports

- W-2 box 1 wages
- W-2 box 2 federal withholding
- 1099-DIV ordinary dividends
- 1099-DIV qualified dividends
- 1099-DIV tax-exempt interest dividends
- 1099-B short-term and long-term gain summaries
- simple refund / amount owed logic when taxable income is zero

---

## What it does not support yet

- Form 1040-NR
- itemized deductions
- dependents / child credits
- education credits
- IRA / HSA adjustments
- self-employment
- state returns
- federal tax table computation for nonzero taxable income
- e-filing

---

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install pypdf pdfplumber
````
---

## File setup

Place all required files in the same folder as `tax1040_simple.py`.

Your folder should look like this:

TaxTool/
- tax1040_simple.py
- 2025 W2.pdf
- 2025-A-s-Individual-Fidelity-Go-Consolidated-Form-1099.pdf
- 2025-Individual-1084-Consolidated-Form-1099.pdf

Notes:

- File names must match exactly (including spaces and capitalization)
- If your file has a different name (for example: `W2_2025.pdf`), update the command accordingly
- You can also use full file paths instead of placing files in the same folder


### Before running

Make sure:
- You are inside the folder where `tax1040_simple.py` is located
- Your PDF files are in the same folder OR you are using full paths
- You use the exact file names shown in your system

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

## Output

It writes:

* `tax_summary.json`
* `tax_report.md`

---

## Windows (PowerShell)

If you are on Windows, use these commands instead of the ones above.

### Activate virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

---

### Install dependencies

```powershell
pip install pypdf pdfplumber
```

---

### Run

#### One line (recommended)

```powershell
python .\tax1040_simple.py --resident-return --tax-year 2025 --w2 ".\2025 W2.pdf" --brokerage-1099 ".\2025-A-s-Individual-Fidelity-Go-Consolidated-Form-1099.pdf" --brokerage-1099 ".\2025-Individual-1084-Consolidated-Form-1099.pdf" --output-json ".\tax_summary.json" --output-report ".\tax_report.md"
```

#### Multiline (PowerShell style)

```powershell
python .\tax1040_simple.py `
--resident-return `
--tax-year 2025 `
--w2 ".\2025 W2.pdf" `
--brokerage-1099 ".\2025-A-s-Individual-Fidelity-Go-Consolidated-Form-1099.pdf" `
--brokerage-1099 ".\2025-Individual-1084-Consolidated-Form-1099.pdf" `
--output-json ".\tax_summary.json" `
--output-report ".\tax_report.md"
```

---

### Notes

* Do not run flags (`--tax-year`, etc.) on separate lines by themselves
* PowerShell does not support `\` for line continuation
* Use backtick `` ` `` for multiline commands
* `source .venv/bin/activate` is macOS/Linux only

---

## Sample output

After running the tool, the following files are generated:

### tax_summary.json

```json
{
  "wages": 9330,
  "ordinary_dividends": 13,
  "qualified_dividends": 9,
  "capital_gain": 10,
  "total_income": 9353,
  "standard_deduction": 14600,
  "taxable_income": 0,
  "federal_tax": 0,
  "federal_withholding": 1146,
  "refund": 1146,
  "amount_owed": 0
}
````

### tax_report.md

```
W-2
- Wages (Box 1): 9330
- Federal withholding (Box 2): 1146

1099-DIV
- Ordinary dividends: 13
- Qualified dividends: 9

1099-B
- Capital gain (short-term + long-term): 10

Form 1040 summary
- Total income: 9353
- Standard deduction: 14600
- Taxable income: 0
- Federal tax: 0
- Refund: 1146
```

### How to interpret

* Wages come from W-2 Box 1
* Withholding comes from W-2 Box 2
* Dividends come from 1099-DIV
* Capital gains come from 1099-B

The tool combines these values and applies the standard deduction to estimate taxable income and refund.

In this example:

* Taxable income is reduced to 0 due to the standard deduction
* All withheld tax is refunded

This output can be directly used as a reference when entering values into tax filing software.

---

## Mapping to Form 1040

The tool maps extracted values from your documents to the corresponding Form 1040 fields.

### Income

| Source        | Document Field                | Form 1040 Line |
|--------------|------------------------------|----------------|
| Wages        | W-2 Box 1                    | Line 1         |
| Ordinary dividends | 1099-DIV Box 1a        | Line 3b        |
| Qualified dividends | 1099-DIV Box 1b       | Line 3a        |
| Capital gains | 1099-B summary              | Line 7         |

---

### Adjustments and deductions

| Component           | Description                  | Form 1040 Line |
|--------------------|------------------------------|----------------|
| Standard deduction | Applied automatically        | Line 12        |

---

### Tax calculation

| Component         | Description                  | Form 1040 Line |
|------------------|------------------------------|----------------|
| Taxable income   | Total income - deductions    | Line 15        |
| Federal tax      | Based on taxable income      | Line 16        |

---

### Payments and refund

| Component              | Source              | Form 1040 Line |
|-----------------------|---------------------|----------------|
| Federal withholding   | W-2 Box 2           | Line 25a       |
| Refund                | Calculated          | Line 34        |
| Amount owed           | Calculated          | Line 37        |

---

### Notes

- Values are rounded to whole dollars as required by the IRS  
- Small or de minimis 1099 statements (not reported to IRS) may be ignored  
- This tool provides an estimated mapping and should be reviewed before filing  

---

## Recommended next upgrades

1. Add explicit 1040 line support for Schedule B and Schedule D detail
2. Add actual federal tax calculation for nonzero taxable income
3. Add support for multiple broker formats, not just Fidelity
4. Add a small web UI with Streamlit
5. Add a checkbox flow: resident 1040 vs nonresident 1040-NR
6. Add tests with your own redacted PDFs

---

## Safety note

Use this as a personal organizer and calculator, not blind filing software.
Always compare against your source docs and final return.

---

## How to file your taxes

This tool does not submit tax returns to the IRS. It prepares and summarizes your data so you can file easily using standard methods.

After running the tool:

1. Review the generated files:
   - `tax_summary.json`
   - `tax_report.md`

2. Use one of the following filing options:

### Option 1: E-file using tax software (recommended)

Enter the extracted values into a tax filing platform such as:
- FreeTaxUSA
- TurboTax

Typical flow:
- Enter W-2 information (wages and withholding)
- Enter 1099-DIV (dividends)
- Enter 1099-B (capital gains)
- Skip any 1099 marked as “not reported to IRS” if applicable
- Review and submit electronically

### Option 2: Manual filing (mail)

- Download Form 1040 from the IRS website
- Fill in values using the tool’s output
- Print, sign, and mail

Note: Manual filing may take longer and has higher risk of errors.

---

## Cost comparison

This tool helps reduce the need for paid tax preparation services.

Typical costs:

- Tax consultant: ~$150–$500+
- TurboTax (federal + state): ~$100+
- FreeTaxUSA:
  - Federal: $0
  - State: ~$15

Using this tool:

- Data extraction and preparation: $0
- Filing (using FreeTaxUSA): ~$0–$15

This allows you to:
- avoid expensive consultant fees
- understand your return before filing
- independently verify your tax data
