#!/usr/bin/env python3
"""
Simple resident Form 1040 helper for W-2 + brokerage 1099 inputs.

What it does
------------
- Extracts key fields from common PDF statements (W-2 and Fidelity-style 1099)
- Maps them to a simple resident Form 1040 summary
- Builds a simplified Schedule D mapping from 1099-B summary totals
- Produces a JSON summary and a readable markdown report

What it does NOT do
-------------------
- File taxes for you
- Support Form 1040-NR
- Handle full Form 8949 logic
- Handle complex credits, itemized deductions, business income, K-1s, rentals, etc.
- Replace a CPA / EA / attorney

Use case
--------
Best for straightforward resident returns with:
- W-2 wages
- 1099-DIV dividends
- 1099-B capital gains
- standard deduction
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable, Optional


# -----------------------------
# Helpers
# -----------------------------

def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def irs_round(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def read_pdf_text(pdf_path: Path) -> str:
    errors = []

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception as exc:  # pragma: no cover
                errors.append(f"pypdf page extract failed: {exc}")
        text = "\n".join(texts)
        if text.strip():
            return text
    except Exception as exc:  # pragma: no cover
        errors.append(f"pypdf failed: {exc}")

    try:
        import pdfplumber  # type: ignore

        texts = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                texts.append(page.extract_text() or "")
        text = "\n".join(texts)
        if text.strip():
            return text
    except Exception as exc:  # pragma: no cover
        errors.append(f"pdfplumber failed: {exc}")

    joined = "; ".join(errors) if errors else "unknown extraction error"
    raise RuntimeError(f"Could not extract text from {pdf_path.name}: {joined}")


def first_decimal(patterns: Iterable[str], text: str) -> Optional[Decimal]:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            raw = match.group(1).replace(",", "")
            try:
                return money(Decimal(raw))
            except Exception:
                continue
    return None


def decimal_from_match(raw: str) -> Decimal:
    return money(Decimal(raw.replace(",", "")))


def find_fidelity_1099b_summary_row(text: str, label: str) -> tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
    """
    Extract proceeds, cost basis, and realized gain/loss from a Fidelity 1099-B summary row.

    We search from the label forward and grab the first 6 decimal-like numbers:
    proceeds, cost basis, market discount, wash sales, realized gain/loss, withholding.
    """
    normalized_text = text.replace("\r", "")
    start = normalized_text.lower().find(label.lower())
    if start == -1:
        return None, None, None

    window = normalized_text[start:start + 500]
    numbers = re.findall(r"-?\d[\d,]*\.\d{2}", window)

    if len(numbers) < 5:
        return None, None, None

    try:
        proceeds = decimal_from_match(numbers[0])
        cost_basis = decimal_from_match(numbers[1])
        realized_gain_loss = decimal_from_match(numbers[4])
        return proceeds, cost_basis, realized_gain_loss
    except Exception:
        return None, None, None


# -----------------------------
# Data models
# -----------------------------

@dataclass
class W2Data:
    wages_box1: Decimal = Decimal("0.00")
    federal_withheld_box2: Decimal = Decimal("0.00")
    social_security_wages_box3: Decimal = Decimal("0.00")
    social_security_tax_box4: Decimal = Decimal("0.00")
    medicare_wages_box5: Decimal = Decimal("0.00")
    medicare_tax_box6: Decimal = Decimal("0.00")
    source_file: str = ""


@dataclass
class Brokerage1099Data:
    de_minimis_not_filed_with_irs: bool = False

    ordinary_dividends_1099div_box1a: Decimal = Decimal("0.00")
    qualified_dividends_1099div_box1b: Decimal = Decimal("0.00")
    tax_exempt_interest_dividends_box12: Decimal = Decimal("0.00")
    foreign_tax_paid_box7: Decimal = Decimal("0.00")
    federal_withholding_1099: Decimal = Decimal("0.00")

    short_term_proceeds: Decimal = Decimal("0.00")
    short_term_cost_basis: Decimal = Decimal("0.00")
    short_term_realized_gain: Decimal = Decimal("0.00")

    long_term_proceeds: Decimal = Decimal("0.00")
    long_term_cost_basis: Decimal = Decimal("0.00")
    long_term_realized_gain: Decimal = Decimal("0.00")

    source_file: str = ""

    @property
    def total_capital_gain(self) -> Decimal:
        return money(self.short_term_realized_gain + self.long_term_realized_gain)


@dataclass
class ScheduleDResult:
    part_i_line_1a_proceeds: str
    part_i_line_1a_cost_basis: str
    part_i_line_1a_gain_or_loss: str
    part_i_line_7_net_short_term_gain_or_loss: str

    part_ii_line_8a_proceeds: str
    part_ii_line_8a_cost_basis: str
    part_ii_line_8a_gain_or_loss: str
    part_ii_line_15_net_long_term_gain_or_loss: str

    part_iii_line_16_combined_net_gain_or_loss: str


@dataclass
class TaxProfile:
    tax_year: int
    filing_status: str = "single"
    resident_return: bool = True
    standard_deduction: Decimal = Decimal("15750.00")


@dataclass
class Form1040SimpleResult:
    line_1a_wages: int
    line_2a_tax_exempt_interest: int
    line_2b_taxable_interest: int
    line_3a_qualified_dividends: int
    line_3b_ordinary_dividends: int
    line_7_capital_gain_or_loss: int
    line_9_total_income: int
    line_10_adjustments: int
    line_11a_agi: int
    line_12_standard_or_itemized_deduction: int
    line_14_total_deductions: int
    line_15_taxable_income: int
    line_16_tax: int
    line_24_total_tax: int
    line_25a_w2_withholding: int
    line_25b_1099_withholding: int
    line_25d_total_withholding: int
    line_33_total_payments: int
    line_34_overpayment: int
    line_35a_refund: int
    line_37_amount_owed: int
    schedule_d: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


# -----------------------------
# Parsers
# -----------------------------

def parse_w2(pdf_path: Path) -> W2Data:
    text = read_pdf_text(pdf_path)

    wages = first_decimal([
        r"BOX\s*1\s*WAGES\s*([0-9,]+(?:\.\d{1,2})?)",
        r"1\s+Wages, tips, other comp\.\s*([0-9,]+(?:\.\d{1,2})?)",
        r"1\s+Wages, tips, other comp\.?\s*([0-9,]+(?:\.\d{1,2})?)",
    ], text) or Decimal("0.00")

    fed = first_decimal([
        r"FED\.\s*INCOME\s*TAX\s*([0-9,]+(?:\.\d{1,2})?)",
        r"2\s+Federal income tax withheld\s*([0-9,]+(?:\.\d{1,2})?)",
    ], text) or Decimal("0.00")

    ss_wages = first_decimal([
        r"3\s+Social security wages\s*([0-9,]+(?:\.\d{1,2})?)",
        r"SOCIAL SECURITY WAGES\s*([0-9,]+(?:\.\d{1,2})?)",
    ], text) or Decimal("0.00")

    ss_tax = first_decimal([
        r"4\s+Social security tax withheld\s*([0-9,]+(?:\.\d{1,2})?)",
        r"SOCIAL SECURITY TAX\s*([0-9,]+(?:\.\d{1,2})?)",
    ], text) or Decimal("0.00")

    medicare_wages = first_decimal([
        r"5\s+Medicare wages and tips\s*([0-9,]+(?:\.\d{1,2})?)",
    ], text) or Decimal("0.00")

    medicare_tax = first_decimal([
        r"6\s+Medicare tax withheld\s*([0-9,]+(?:\.\d{1,2})?)",
        r"MEDICARE TAX\s*([0-9,]+(?:\.\d{1,2})?)",
    ], text) or Decimal("0.00")

    return W2Data(
        wages_box1=wages,
        federal_withheld_box2=fed,
        social_security_wages_box3=ss_wages,
        social_security_tax_box4=ss_tax,
        medicare_wages_box5=medicare_wages,
        medicare_tax_box6=medicare_tax,
        source_file=pdf_path.name,
    )


def parse_fidelity_1099(pdf_path: Path) -> Brokerage1099Data:
    text = read_pdf_text(pdf_path)

    ordinary_dividends = first_decimal([
        r"1a\s+Total Ordinary Dividends\s*\.*\s*([0-9,]+(?:\.\d{1,2})?)",
    ], text) or Decimal("0.00")

    qualified_dividends = first_decimal([
        r"1b\s+Qualified Dividends\s*\.*\s*([0-9,]+(?:\.\d{1,2})?)",
    ], text) or Decimal("0.00")

    tax_exempt_interest = first_decimal([
        r"12\s+Exempt Interest Dividends\s*\.*\s*([0-9,]+(?:\.\d{1,2})?)",
        r"8\s+Tax-Exempt Interest\s*\.*\s*([0-9,]+(?:\.\d{1,2})?)",
    ], text) or Decimal("0.00")

    foreign_tax_paid = first_decimal([
        r"7\s+Foreign Tax Paid\s*\.*\s*([0-9,]+(?:\.\d{1,2})?)",
    ], text) or Decimal("0.00")

    federal_withholding_1099 = first_decimal([
        r"4\s+Federal Income Tax Withheld\s*\.*\s*([0-9,]+(?:\.\d{1,2})?)",
        r"Federal Income Tax Withheld\s*\.*\s*([0-9,]+(?:\.\d{1,2})?)",
    ], text) or Decimal("0.00")

    short_term_proceeds, short_term_cost_basis, short_term_summary_gain = find_fidelity_1099b_summary_row(
        text,
        "Short-term transactions for which basis is reported to the IRS",
    )

    long_term_proceeds, long_term_cost_basis, long_term_summary_gain = find_fidelity_1099b_summary_row(
        text,
        "Long-term transactions for which basis is reported to the IRS",
    )

    box_a_short_term_gain = first_decimal([
        r"Box A Short-Term Realized Gain\s*([0-9,]+(?:\.\d{1,2})?)",
    ], text)

    box_a_short_term_loss = first_decimal([
        r"Box A Short-Term Realized Loss\s*(-?[0-9,]+(?:\.\d{1,2})?)",
    ], text)

    box_d_long_term_gain = first_decimal([
        r"Box D Long-Term Realized Gain\s*([0-9,]+(?:\.\d{1,2})?)",
    ], text)

    box_d_long_term_loss = first_decimal([
        r"Box D Long-Term Realized Loss\s*(-?[0-9,]+(?:\.\d{1,2})?)",
    ], text)

    if short_term_summary_gain is not None:
        net_short = short_term_summary_gain
    elif box_a_short_term_gain is not None or box_a_short_term_loss is not None:
        net_short = money((box_a_short_term_gain or Decimal("0.00")) + (box_a_short_term_loss or Decimal("0.00")))
    else:
        net_short = Decimal("0.00")

    if long_term_summary_gain is not None:
        net_long = long_term_summary_gain
    elif box_d_long_term_gain is not None or box_d_long_term_loss is not None:
        net_long = money((box_d_long_term_gain or Decimal("0.00")) + (box_d_long_term_loss or Decimal("0.00")))
    else:
        net_long = Decimal("0.00")

    normalized = re.sub(r"\s+", "", text.lower())
    de_minimis = (
        "deminimisrulesthisformisnotfiledwiththeirs" in normalized
        or "duetodeminimisrulesthisformisnotfiledwiththeirs" in normalized
        or "notreportedtotheirs" in normalized
    )

    return Brokerage1099Data(
        de_minimis_not_filed_with_irs=de_minimis,
        ordinary_dividends_1099div_box1a=ordinary_dividends,
        qualified_dividends_1099div_box1b=qualified_dividends,
        tax_exempt_interest_dividends_box12=tax_exempt_interest,
        foreign_tax_paid_box7=foreign_tax_paid,
        federal_withholding_1099=federal_withholding_1099,
        short_term_proceeds=short_term_proceeds or Decimal("0.00"),
        short_term_cost_basis=short_term_cost_basis or Decimal("0.00"),
        short_term_realized_gain=net_short,
        long_term_proceeds=long_term_proceeds or Decimal("0.00"),
        long_term_cost_basis=long_term_cost_basis or Decimal("0.00"),
        long_term_realized_gain=net_long,
        source_file=pdf_path.name,
    )


# -----------------------------
# Tax computation
# -----------------------------

def build_simple_1040(profile: TaxProfile, w2s: list[W2Data], brokerage_forms: list[Brokerage1099Data]) -> Form1040SimpleResult:
    notes: list[str] = []

    # Include all brokerage forms in the taxpayer return mapping.
    # "Not filed with the IRS" on a composite statement does NOT mean the amounts
    # should be skipped from the taxpayer's own return.
    included_brokerage_forms = brokerage_forms

    flagged_brokerage_forms = [b for b in brokerage_forms if b.de_minimis_not_filed_with_irs]
    if flagged_brokerage_forms:
        flagged = ", ".join(b.source_file for b in flagged_brokerage_forms)
        notes.append(
            "Included brokerage statements even though they were marked de minimis / not filed with the IRS "
            f"on the statement: {flagged}"
        )

    if not profile.resident_return:
        notes.append("Profile marked as nonresident. This tool is only for simple resident Form 1040 flows, not 1040-NR.")

    wages = money(sum((w.wages_box1 for w in w2s), Decimal("0.00")))
    w2_withholding = money(sum((w.federal_withheld_box2 for w in w2s), Decimal("0.00")))

    ordinary_dividends = money(sum((b.ordinary_dividends_1099div_box1a for b in included_brokerage_forms), Decimal("0.00")))
    qualified_dividends = money(sum((b.qualified_dividends_1099div_box1b for b in included_brokerage_forms), Decimal("0.00")))
    tax_exempt_interest = money(sum((b.tax_exempt_interest_dividends_box12 for b in included_brokerage_forms), Decimal("0.00")))
    withholding_1099 = money(sum((b.federal_withholding_1099 for b in included_brokerage_forms), Decimal("0.00")))

    schedule_d_short_term_proceeds = money(sum((b.short_term_proceeds for b in included_brokerage_forms), Decimal("0.00")))
    schedule_d_short_term_cost_basis = money(sum((b.short_term_cost_basis for b in included_brokerage_forms), Decimal("0.00")))
    schedule_d_short_term_gain = money(sum((b.short_term_realized_gain for b in included_brokerage_forms), Decimal("0.00")))

    schedule_d_long_term_proceeds = money(sum((b.long_term_proceeds for b in included_brokerage_forms), Decimal("0.00")))
    schedule_d_long_term_cost_basis = money(sum((b.long_term_cost_basis for b in included_brokerage_forms), Decimal("0.00")))
    schedule_d_long_term_gain = money(sum((b.long_term_realized_gain for b in included_brokerage_forms), Decimal("0.00")))

    capital_gain = money(schedule_d_short_term_gain + schedule_d_long_term_gain)

    schedule_d = ScheduleDResult(
        part_i_line_1a_proceeds=str(schedule_d_short_term_proceeds),
        part_i_line_1a_cost_basis=str(schedule_d_short_term_cost_basis),
        part_i_line_1a_gain_or_loss=str(schedule_d_short_term_gain),
        part_i_line_7_net_short_term_gain_or_loss=str(schedule_d_short_term_gain),
        part_ii_line_8a_proceeds=str(schedule_d_long_term_proceeds),
        part_ii_line_8a_cost_basis=str(schedule_d_long_term_cost_basis),
        part_ii_line_8a_gain_or_loss=str(schedule_d_long_term_gain),
        part_ii_line_15_net_long_term_gain_or_loss=str(schedule_d_long_term_gain),
        part_iii_line_16_combined_net_gain_or_loss=str(capital_gain),
    )

    taxable_interest = Decimal("0.00")
    adjustments = Decimal("0.00")

    # Tax-exempt interest goes on line 2a but is not included in taxable income.
    total_income = money(wages + taxable_interest + ordinary_dividends + capital_gain)
    agi = money(total_income - adjustments)
    total_deductions = money(profile.standard_deduction)
    taxable_income = money(max(agi - total_deductions, Decimal("0.00")))

    # Still intentionally simplified.
    tax = Decimal("0.00")
    if taxable_income > 0:
        notes.append(
            "Taxable income is above zero. This starter version does not compute full federal tax tables or qualified dividend worksheet logic yet."
        )

    total_tax = tax
    total_withholding = money(w2_withholding + withholding_1099)
    total_payments = total_withholding

    overpayment = money(max(total_payments - total_tax, Decimal("0.00")))
    refund = overpayment
    amount_owed = money(max(total_tax - total_payments, Decimal("0.00")))

    return Form1040SimpleResult(
        line_1a_wages=irs_round(wages),
        line_2a_tax_exempt_interest=irs_round(tax_exempt_interest),
        line_2b_taxable_interest=irs_round(taxable_interest),
        line_3a_qualified_dividends=irs_round(qualified_dividends),
        line_3b_ordinary_dividends=irs_round(ordinary_dividends),
        line_7_capital_gain_or_loss=irs_round(capital_gain),
        line_9_total_income=irs_round(total_income),
        line_10_adjustments=irs_round(adjustments),
        line_11a_agi=irs_round(agi),
        line_12_standard_or_itemized_deduction=irs_round(profile.standard_deduction),
        line_14_total_deductions=irs_round(total_deductions),
        line_15_taxable_income=irs_round(taxable_income),
        line_16_tax=irs_round(tax),
        line_24_total_tax=irs_round(total_tax),
        line_25a_w2_withholding=irs_round(w2_withholding),
        line_25b_1099_withholding=irs_round(withholding_1099),
        line_25d_total_withholding=irs_round(total_withholding),
        line_33_total_payments=irs_round(total_payments),
        line_34_overpayment=irs_round(overpayment),
        line_35a_refund=irs_round(refund),
        line_37_amount_owed=irs_round(amount_owed),
        schedule_d=asdict(schedule_d),
        notes=notes,
    )


# -----------------------------
# Reporting
# -----------------------------

def build_report(profile: TaxProfile, w2s: list[W2Data], brokerage_forms: list[Brokerage1099Data], result: Form1040SimpleResult) -> str:
    lines: list[str] = []
    lines.append(f"# Simple Form 1040 Mapping Report ({profile.tax_year})")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")

    for w in w2s:
        lines.append(f"### W-2: {w.source_file}")
        lines.append(f"- W-2 Box 1 wages: ${w.wages_box1}")
        lines.append(f"- W-2 Box 2 federal withholding: ${w.federal_withheld_box2}")
        lines.append("")

    for b in brokerage_forms:
        lines.append(f"### Brokerage 1099: {b.source_file}")
        lines.append(f"- 1099-DIV Box 1a ordinary dividends: ${b.ordinary_dividends_1099div_box1a}")
        lines.append(f"- 1099-DIV Box 1b qualified dividends: ${b.qualified_dividends_1099div_box1b}")
        lines.append(f"- 1099-DIV Box 12 tax-exempt interest dividends: ${b.tax_exempt_interest_dividends_box12}")
        lines.append(f"- 1099 federal withholding: ${b.federal_withholding_1099}")
        lines.append(f"- 1099-B short-term proceeds: ${b.short_term_proceeds}")
        lines.append(f"- 1099-B short-term cost basis: ${b.short_term_cost_basis}")
        lines.append(f"- 1099-B net short-term gain: ${b.short_term_realized_gain}")
        lines.append(f"- 1099-B long-term proceeds: ${b.long_term_proceeds}")
        lines.append(f"- 1099-B long-term cost basis: ${b.long_term_cost_basis}")
        lines.append(f"- 1099-B net long-term gain: ${b.long_term_realized_gain}")
        lines.append(f"- 1099-B total capital gain: ${b.total_capital_gain}")
        if b.de_minimis_not_filed_with_irs:
            lines.append("- Note: statement text says de minimis / not filed with the IRS, but values are still included in taxpayer mapping")
        lines.append("")

    included_brokerage_forms = brokerage_forms

    short_term_proceeds = sum((b.short_term_proceeds for b in included_brokerage_forms), Decimal("0.00"))
    short_term_basis = sum((b.short_term_cost_basis for b in included_brokerage_forms), Decimal("0.00"))
    short_term_gain = sum((b.short_term_realized_gain for b in included_brokerage_forms), Decimal("0.00"))

    long_term_proceeds = sum((b.long_term_proceeds for b in included_brokerage_forms), Decimal("0.00"))
    long_term_basis = sum((b.long_term_cost_basis for b in included_brokerage_forms), Decimal("0.00"))
    long_term_gain = sum((b.long_term_realized_gain for b in included_brokerage_forms), Decimal("0.00"))

    net_gain = short_term_gain + long_term_gain

    lines.append("## Form 8949 / Schedule D mapping (copy-ready)")
    lines.append("")

    lines.append("### Short-term (Part I - Line 1a, covered, basis reported)")
    lines.append(f"- Proceeds: ${money(short_term_proceeds)}")
    lines.append(f"- Cost basis: ${money(short_term_basis)}")
    lines.append(f"- Gain: ${money(short_term_gain)}")
    lines.append("")

    lines.append("### Long-term (Part II - Line 8a, covered, basis reported)")
    lines.append(f"- Proceeds: ${money(long_term_proceeds)}")
    lines.append(f"- Cost basis: ${money(long_term_basis)}")
    lines.append(f"- Gain: ${money(long_term_gain)}")
    lines.append("")

    lines.append("### Schedule D totals")
    lines.append(f"- Line 7 (short-term gain): ${money(short_term_gain)}")
    lines.append(f"- Line 15 (long-term gain): ${money(long_term_gain)}")
    lines.append(f"- Line 16 (net capital gain): ${money(net_gain)}")
    lines.append("")

    lines.append("## Form 1040 mapping")
    lines.append("")
    mapping = {
        "Line 1a": f"Wages = {result.line_1a_wages}",
        "Line 2a": f"Tax-exempt interest = {result.line_2a_tax_exempt_interest}",
        "Line 2b": f"Taxable interest = {result.line_2b_taxable_interest}",
        "Line 3a": f"Qualified dividends = {result.line_3a_qualified_dividends}",
        "Line 3b": f"Ordinary dividends = {result.line_3b_ordinary_dividends}",
        "Line 7": f"Capital gain or loss from Schedule D Part III Line 16 = {result.line_7_capital_gain_or_loss}",
        "Line 9": f"Total income = {result.line_9_total_income}",
        "Line 10": f"Adjustments = {result.line_10_adjustments}",
        "Line 11a": f"AGI = {result.line_11a_agi}",
        "Line 12": f"Standard deduction = {result.line_12_standard_or_itemized_deduction}",
        "Line 14": f"Total deductions = {result.line_14_total_deductions}",
        "Line 15": f"Taxable income = {result.line_15_taxable_income}",
        "Line 16": f"Tax = {result.line_16_tax}",
        "Line 24": f"Total tax = {result.line_24_total_tax}",
        "Line 25a": f"W-2 withholding = {result.line_25a_w2_withholding}",
        "Line 25b": f"1099 withholding = {result.line_25b_1099_withholding}",
        "Line 25d": f"Total withholding = {result.line_25d_total_withholding}",
        "Line 33": f"Total payments = {result.line_33_total_payments}",
        "Line 34": f"Overpayment = {result.line_34_overpayment}",
        "Line 35a": f"Refund = {result.line_35a_refund}",
        "Line 37": f"Amount owed = {result.line_37_amount_owed}",
    }
    for line_name, value in mapping.items():
        lines.append(f"- {line_name}: {value}")

    if result.notes:
        lines.append("")
        lines.append("## Notes")
        for note in result.notes:
            lines.append(f"- {note}")

    lines.append("")
    lines.append("## Important limits")
    lines.append("- This tool is for simple resident 1040 flows only.")
    lines.append("- Schedule D is currently a simplified mapping based on 1099-B totals.")
    lines.append("- Form 8949 is not implemented.")
    lines.append("- It does not support 1040-NR.")
    lines.append("- If taxable income is above zero, extend the federal tax calculation before relying on it.")
    lines.append("- Always compare output against the source forms and the final return.")

    return "\n".join(lines)


# -----------------------------
# CLI
# -----------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Simple Form 1040 helper for W-2 + Fidelity 1099 PDFs")
    parser.add_argument("--w2", action="append", default=[], help="Path to a W-2 PDF. Can be passed multiple times.")
    parser.add_argument("--brokerage-1099", action="append", default=[], help="Path to a brokerage 1099 PDF. Can be passed multiple times.")
    parser.add_argument("--tax-year", type=int, default=2025)
    parser.add_argument("--filing-status", default="single", choices=["single"])
    parser.add_argument("--resident-return", action="store_true", default=True, help="Mark this as a resident Form 1040 flow.")
    parser.add_argument("--output-json", default="tax_summary.json")
    parser.add_argument("--output-report", default="tax_report.md")
    args = parser.parse_args()

    if not args.w2 and not args.brokerage_1099:
        raise SystemExit("Please provide at least one --w2 or --brokerage-1099 PDF.")

    standard_deduction_by_year = {
        2025: Decimal("15750.00"),
    }
    standard_deduction = standard_deduction_by_year.get(args.tax_year)
    if standard_deduction is None:
        raise SystemExit(f"No standard deduction configured for tax year {args.tax_year}.")

    profile = TaxProfile(
        tax_year=args.tax_year,
        filing_status=args.filing_status,
        resident_return=args.resident_return,
        standard_deduction=standard_deduction,
    )

    w2s = [parse_w2(Path(path)) for path in args.w2]
    brokerage_forms = [parse_fidelity_1099(Path(path)) for path in args.brokerage_1099]
    result = build_simple_1040(profile, w2s, brokerage_forms)

    payload = {
        "profile": asdict(profile),
        "w2s": [asdict(w) for w in w2s],
        "brokerage_1099s": [asdict(b) | {"total_capital_gain": str(b.total_capital_gain)} for b in brokerage_forms],
        "form_1040_summary": asdict(result),
    }

    output_json = Path(args.output_json)
    output_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    output_report = Path(args.output_report)
    output_report.write_text(build_report(profile, w2s, brokerage_forms, result), encoding="utf-8")

    print(f"Wrote {output_json}")
    print(f"Wrote {output_report}")


if __name__ == "__main__":
    main()