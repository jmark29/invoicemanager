#!/usr/bin/env python3
"""
Invoice Generator - Template-based DOCX invoice creation.

Uses an existing DOCX as template, clones it, and replaces variable fields
(date, invoice number, period, line items, amounts) via XML editing.

Usage:
    python3 generate_invoice.py --month 2026-01 --client drs [--output-dir .]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from calendar import monthrange

# ─── Paths ───────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
TRACKING_PATH = SCRIPT_DIR / "tracking.json"

NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ET.register_namespace("w", NS)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_tracking():
    with open(TRACKING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tracking(tracking):
    with open(TRACKING_PATH, "w", encoding="utf-8") as f:
        json.dump(tracking, f, indent=2, ensure_ascii=False)


def format_eur(amount):
    """Format a number as German EUR string: 1.234,56 €"""
    d = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # Format with German locale style
    int_part = int(d)
    dec_part = abs(d - int_part)
    dec_str = f"{dec_part:.2f}"[2:]  # get 2 decimal digits

    # Add thousand separators
    int_str = f"{abs(int_part):,}".replace(",", ".")
    if int_part < 0:
        int_str = "-" + int_str

    return f"{int_str},{dec_str} \u20ac"


def get_last_day(year, month):
    """Return last day of given month."""
    return monthrange(year, month)[1]


def get_period_string(year, month):
    """Return period string like '01.01.2025 bis 31.01.2025'"""
    last_day = get_last_day(year, month)
    return f"01.{month:02d}.{year} bis {last_day:02d}.{month:02d}.{year}"


def get_invoice_number(config, client_id, year, month):
    """Generate invoice number like 202501-02 (prefix AR only used in filename)"""
    client = config["clients"][client_id]
    return f"{year}{month:02d}-{client['id']}"


def get_invoice_filename(config, client_id, year, month):
    """Generate invoice filename like AR202501-02.docx"""
    client = config["clients"][client_id]
    return f"{config['invoice_numbering']['prefix']}{year}{month:02d}-{client['id']}.docx"


# ─── XML Editing ─────────────────────────────────────────────────────

def get_paragraph_text(p_elem):
    """Get the combined text from all runs in a paragraph."""
    texts = []
    for t in p_elem.iter(f"{{{NS}}}t"):
        if t.text:
            texts.append(t.text)
    return "".join(texts)


def set_paragraph_text(p_elem, new_text):
    """Set text of a paragraph by putting all text in the first run and clearing the rest.
    This handles the case where text is split across multiple w:r elements."""
    t_elements = list(p_elem.iter(f"{{{NS}}}t"))
    if not t_elements:
        return False
    # Put all text in the first element
    t_elements[0].text = new_text
    # Set xml:space="preserve" to keep whitespace
    t_elements[0].set(f"{{http://www.w3.org/XML/1998/namespace}}space", "preserve")
    # Clear all subsequent text elements
    for t in t_elements[1:]:
        t.text = ""
    return True


def set_cell_text(cell_elem, new_text):
    """Set text in a table cell, handling multiple runs."""
    for p in cell_elem.iter(f"{{{NS}}}p"):
        t_elements = list(p.iter(f"{{{NS}}}t"))
        if t_elements:
            t_elements[0].text = new_text
            t_elements[0].set(f"{{http://www.w3.org/XML/1998/namespace}}space", "preserve")
            for t in t_elements[1:]:
                t.text = ""
            return True
    return False


def find_table(root):
    """Find the main invoice table in the document."""
    tables = list(root.iter(f"{{{NS}}}tbl"))
    if tables:
        return tables[0]
    return None


def get_row_texts(row):
    """Extract all text from a table row."""
    texts = []
    for t in row.iter(f"{{{NS}}}t"):
        if t.text:
            texts.append(t.text.strip())
    return texts


def get_cell_text(cell):
    """Get combined text from a table cell."""
    texts = []
    for t in cell.iter(f"{{{NS}}}t"):
        if t.text:
            texts.append(t.text)
    return "".join(texts).strip()


def update_amount_in_row(row, new_amount_str):
    """Update the amount (last cell) in a table row."""
    cells = list(row.iter(f"{{{NS}}}tc"))
    if cells:
        last_cell = cells[-1]
        cell_text = get_cell_text(last_cell)
        if "\u20ac" in cell_text:
            set_cell_text(last_cell, new_amount_str)
            return True
    return False


def update_label_in_row(row, new_label):
    """Update the label (middle cell) in a table row."""
    cells = list(row.iter(f"{{{NS}}}tc"))
    if len(cells) >= 2:
        middle_cell = cells[1]
        cell_text = get_cell_text(middle_cell)
        if cell_text:
            set_cell_text(middle_cell, new_label)
            return True
    return False


# ─── Main Generation Logic ───────────────────────────────────────────

def generate_invoice(
    year: int,
    month: int,
    client_id: str,
    line_item_amounts: dict,
    extra_items: list = None,
    invoice_date: date = None,
    output_dir: Path = None,
):
    """
    Generate an invoice by cloning the template and updating fields.

    Args:
        year: Invoice year
        month: Invoice month (1-12)
        client_id: Client identifier (e.g., 'drs')
        line_item_amounts: Dict mapping position number to amount, e.g. {3: 1800.00, 4: 2851.20, 5: 4673.70, 6: 2512.79}
        extra_items: List of dicts with 'label' and 'amount' for optional items (e.g., travel costs)
        invoice_date: Override invoice date (default: today)
        output_dir: Where to write the output (default: BASE_DIR)

    Returns:
        Path to the generated DOCX file.
    """
    config = load_config()

    if client_id not in config["clients"]:
        raise ValueError(f"Unknown client: {client_id}")

    if output_dir is None:
        output_dir = BASE_DIR

    if invoice_date is None:
        invoice_date = date.today()

    # Determine template
    template_name = config["template_file"]
    template_path = BASE_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    # Generate invoice number
    inv_number = get_invoice_number(config, client_id, year, month)

    # Build complete line items
    items = config["line_items"][client_id]
    all_amounts = {}
    for item in items:
        pos = item["pos"]
        if item["type"] == "fixed":
            all_amounts[pos] = item["amount"]
        elif pos in line_item_amounts:
            all_amounts[pos] = line_item_amounts[pos]
        else:
            raise ValueError(f"Missing amount for position {pos} ({item['label']})")

    # Calculate totals
    net_total = sum(all_amounts.values())
    if extra_items:
        for ei in extra_items:
            net_total += ei["amount"]

    vat_rate = Decimal(str(config["vat_rate"]))
    net_decimal = Decimal(str(net_total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    vat_amount = (net_decimal * vat_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    gross_total = net_decimal + vat_amount

    # ─── Clone and edit template ─────────────────────────────────
    work_dir = Path("/tmp/invoice_gen_work")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    unpacked_dir = work_dir / "unpacked"

    # Unpack
    with zipfile.ZipFile(template_path, "r") as z:
        z.extractall(unpacked_dir)

    # Parse document.xml
    doc_xml_path = unpacked_dir / "word" / "document.xml"
    tree = ET.parse(doc_xml_path)
    root = tree.getroot()

    # ─── Replace header fields ───────────────────────────────────
    # Use paragraph-level replacement to handle text split across runs

    period_str = get_period_string(year, month)
    date_str = invoice_date.strftime("%d.%m.%Y")

    for p_elem in root.iter(f"{{{NS}}}p"):
        p_text = get_paragraph_text(p_elem)

        if p_text.startswith("Rechnung "):
            set_paragraph_text(p_elem, f"Rechnung {inv_number}")
        elif p_text.startswith("Leistungszeitraum "):
            set_paragraph_text(p_elem, f"Leistungszeitraum {period_str}")
        elif p_text.startswith("Wiesbaden, "):
            set_paragraph_text(p_elem, f"Wiesbaden, {date_str}")

    # ─── Update table amounts ────────────────────────────────────
    table = find_table(root)
    if table is None:
        raise RuntimeError("Could not find invoice table in template")

    rows = list(table.iter(f"{{{NS}}}tr"))

    # Map rows to positions by finding the position number in first cell
    for row in rows:
        texts = get_row_texts(row)
        if not texts:
            continue

        first_text = texts[0].strip()

        # Check if this is a line item row (starts with a number)
        if first_text.isdigit():
            pos = int(first_text)
            if pos in all_amounts:
                amount_str = format_eur(all_amounts[pos])
                update_amount_in_row(row, amount_str)
                # Also update label if it changed
                item_config = next((i for i in items if i["pos"] == pos), None)
                if item_config:
                    update_label_in_row(row, item_config["label"])

        # Update summary rows
        joined = " ".join(texts)
        if "Netto-Rechnungsbetrag" in joined:
            update_amount_in_row(row, format_eur(net_decimal))
        elif "Umsatzsteuer 19%" in joined:
            update_amount_in_row(row, format_eur(vat_amount))
        elif "Brutto-Rechnungsbetrag" in joined:
            update_amount_in_row(row, format_eur(gross_total))

    # ─── Handle extra items (TODO: add rows if needed) ───────────
    # For now, extra items need to be in the template already
    # Future: dynamically add/remove table rows

    # ─── Write updated XML ───────────────────────────────────────
    tree.write(doc_xml_path, xml_declaration=True, encoding="UTF-8")

    # ─── Repack DOCX ─────────────────────────────────────────────
    output_filename = get_invoice_filename(config, client_id, year, month)
    output_path = output_dir / output_filename

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for root_dir, dirs, files in os.walk(unpacked_dir):
            for file in files:
                file_path = Path(root_dir) / file
                arcname = file_path.relative_to(unpacked_dir)
                zout.write(file_path, arcname)

    # ─── Clean up ────────────────────────────────────────────────
    shutil.rmtree(work_dir)

    # ─── Update tracking ─────────────────────────────────────────
    tracking = load_tracking()
    inv_key = f"{year}{month:02d}-{config['clients'][client_id]['id']}"
    tracking["generated_invoices"][inv_key] = {
        "client": client_id,
        "period": f"{year}-{month:02d}",
        "invoice_date": invoice_date.isoformat(),
        "line_items": {str(k): v for k, v in all_amounts.items()},
        "net_total": float(net_decimal),
        "vat": float(vat_amount),
        "gross_total": float(gross_total),
    }
    if extra_items:
        for i, ei in enumerate(extra_items):
            tracking["generated_invoices"][inv_key]["line_items"][f"extra_{i}_{ei['label']}"] = ei["amount"]

    tracking["_meta"]["last_updated"] = date.today().isoformat()
    save_tracking(tracking)

    print(f"Invoice generated: {output_path}")
    print(f"  Number:  {inv_number}")
    print(f"  Period:  {period_str}")
    print(f"  Date:    {date_str}")
    print(f"  Net:     {format_eur(net_decimal)}")
    print(f"  VAT:     {format_eur(vat_amount)}")
    print(f"  Gross:   {format_eur(gross_total)}")

    return output_path


# ─── Upwork Processing ───────────────────────────────────────────────

def process_upwork_transactions(xlsx_path, target_month_year, target_month):
    """
    Process Upwork transactions XLSX and assign them to a target month.

    Upwork billing periods are weekly and can span month boundaries.
    A transaction is assigned to a month based on the END date of its period.

    Returns:
        tuple: (total_amount, assigned_transactions)
    """
    import openpyxl

    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb["data"]

    tracking = load_tracking()
    assigned_txns = tracking.get("upwork_transactions", {})

    total = Decimal("0.00")
    new_assignments = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        tx_date_str, tx_id, tx_type, tx_summary, tx_desc, ref_id, amount, currency, payment = row

        if not tx_id or not amount:
            continue

        tx_id_str = str(int(tx_id)) if isinstance(tx_id, (int, float)) else str(tx_id)

        # Skip if already assigned
        if tx_id_str in assigned_txns:
            continue

        # Parse the period from summary: "Invoice for Feb 16-Feb 22, 2026"
        period_match = re.search(
            r"Invoice for (\w+ \d+)[,-]\s*(\w+ \d+),?\s*(\d{4})",
            str(tx_summary) if tx_summary else ""
        )

        if not period_match:
            # Try alternative format: "Invoice for Dec 29, 2025-Jan 4, 2026"
            period_match2 = re.search(
                r"Invoice for (\w+ \d+),?\s*(\d{4})\s*-\s*(\w+ \d+),?\s*(\d{4})",
                str(tx_summary) if tx_summary else ""
            )
            if period_match2:
                end_month_name = period_match2.group(3).split()[0]
                end_year = int(period_match2.group(4))
            else:
                continue
        else:
            end_date_str = period_match.group(2)
            end_year = int(period_match.group(3))
            end_month_name = end_date_str.split()[0]

        # Map month name to number
        month_map = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
        }
        end_month = month_map.get(end_month_name, 0)

        # Check if this transaction belongs to target month
        if end_year == target_month_year and end_month == target_month:
            tx_amount = Decimal(str(amount))
            total += tx_amount
            new_assignments.append({
                "tx_id": tx_id_str,
                "amount": float(tx_amount),
                "period": str(tx_summary),
                "ref_id": str(ref_id) if ref_id else "",
            })

    wb.close()
    return float(total), new_assignments


def assign_upwork_to_month(xlsx_path, year, month, invoice_number):
    """Assign Upwork transactions to a month and update tracking."""
    total, assignments = process_upwork_transactions(xlsx_path, year, month)

    if assignments:
        tracking = load_tracking()
        for a in assignments:
            tracking["upwork_transactions"][a["tx_id"]] = {
                "assigned_month": f"{year}-{month:02d}",
                "assigned_invoice": invoice_number,
                "amount": a["amount"],
                "period": a["period"],
                "ref_id": a["ref_id"],
            }
        save_tracking(tracking)

    return total, assignments


# ─── Working Days Calculation ────────────────────────────────────────

# Hessen public holidays (fixed dates + Easter-dependent)
def get_hessen_holidays(year):
    """Get public holidays for Hessen, Germany for a given year."""
    from datetime import timedelta

    # Easter calculation (Anonymous Gregorian algorithm)
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    easter = date(year, month, day)

    holidays = [
        date(year, 1, 1),     # Neujahr
        easter - timedelta(days=2),  # Karfreitag
        easter + timedelta(days=1),  # Ostermontag
        date(year, 5, 1),     # Tag der Arbeit
        easter + timedelta(days=39), # Christi Himmelfahrt
        easter + timedelta(days=50), # Pfingstmontag
        easter + timedelta(days=60), # Fronleichnam (Hessen!)
        date(year, 10, 3),    # Tag der Deutschen Einheit
        date(year, 12, 25),   # 1. Weihnachtstag
        date(year, 12, 26),   # 2. Weihnachtstag
    ]
    return set(holidays)


def count_working_days(year, month):
    """Count working days in a month (excluding weekends and Hessen holidays)."""
    holidays = get_hessen_holidays(year)
    last_day = get_last_day(year, month)
    count = 0
    for day in range(1, last_day + 1):
        d = date(year, month, day)
        if d.weekday() < 5 and d not in holidays:  # Mon-Fri, not holiday
            count += 1
    return count


def distribute_cost_by_working_days(total_amount, months_list):
    """
    Distribute a total cost across months proportional to working days.

    Args:
        total_amount: Total amount to distribute
        months_list: List of (year, month) tuples

    Returns:
        Dict mapping (year, month) tuple to allocated amount
    """
    working_days = {}
    for ym in months_list:
        working_days[ym] = count_working_days(ym[0], ym[1])

    total_days = sum(working_days.values())
    if total_days == 0:
        raise ValueError("No working days in the given months")

    distribution = {}
    remaining = Decimal(str(total_amount))

    for i, ym in enumerate(months_list):
        if i == len(months_list) - 1:
            # Last month gets the remainder to avoid rounding issues
            distribution[ym] = float(remaining)
        else:
            share = (Decimal(str(total_amount)) * Decimal(str(working_days[ym])) / Decimal(str(total_days))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            distribution[ym] = float(share)
            remaining -= share

    return distribution


# ─── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate monthly invoice")
    parser.add_argument("--month", required=True, help="Target month (YYYY-MM)")
    parser.add_argument("--client", default="drs", help="Client ID")
    parser.add_argument("--date", help="Invoice date (YYYY-MM-DD, default: today)")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--pos3", type=float, help="Amount for Pos 3 (Junior FM)")
    parser.add_argument("--pos4", type=float, help="Amount for Pos 4 (Server/AWS)")
    parser.add_argument("--pos5", type=float, help="Amount for Pos 5 (Mobile Dev / Upwork)")
    parser.add_argument("--pos6", type=float, help="Amount for Pos 6 (QA/BA)")
    parser.add_argument("--upwork-xlsx", help="Path to Upwork transactions XLSX")
    parser.add_argument("--dry-run", action="store_true", help="Show calculations without generating")

    args = parser.parse_args()

    # Parse month
    year, month = map(int, args.month.split("-"))

    # Parse date
    inv_date = date.today()
    if args.date:
        inv_date = date.fromisoformat(args.date)

    # Output dir
    out_dir = Path(args.output_dir) if args.output_dir else BASE_DIR

    # Collect amounts
    amounts = {}
    if args.pos3 is not None:
        amounts[3] = args.pos3
    if args.pos4 is not None:
        amounts[4] = args.pos4
    if args.pos5 is not None:
        amounts[5] = args.pos5
    if args.pos6 is not None:
        amounts[6] = args.pos6

    # Process Upwork if provided and pos5 not manually set
    upwork_txns = []
    if args.upwork_xlsx and 5 not in amounts:
        if args.dry_run:
            # Dry run: only calculate, don't save to tracking
            total, txns = process_upwork_transactions(args.upwork_xlsx, year, month)
            upwork_txns = txns
        else:
            inv_number = get_invoice_number(load_config(), args.client, year, month)
            total, txns = assign_upwork_to_month(args.upwork_xlsx, year, month, inv_number)
            upwork_txns = txns
        amounts[5] = total
        print(f"\nUpwork transactions for {year}-{month:02d}:")
        for t in upwork_txns:
            print(f"  {t['tx_id']}: {format_eur(t['amount'])} ({t['period']})")
        print(f"  Total: {format_eur(total)}\n")

    if args.dry_run:
        config = load_config()
        items = config["line_items"][args.client]
        print(f"Dry run for {year}-{month:02d}:")
        net = Decimal("0")
        for item in items:
            pos = item["pos"]
            if item["type"] == "fixed":
                amt = Decimal(str(item["amount"]))
            elif pos in amounts:
                amt = Decimal(str(amounts[pos]))
            else:
                print(f"  Pos {pos}: *** MISSING ***")
                continue
            net += amt
            print(f"  Pos {pos}: {item['label']} = {format_eur(amt)}")
        vat = (net * Decimal(str(config["vat_rate"]))).quantize(Decimal("0.01"), ROUND_HALF_UP)
        print(f"\n  Net:   {format_eur(net)}")
        print(f"  VAT:   {format_eur(vat)}")
        print(f"  Gross: {format_eur(net + vat)}")
        return

    # Check all required amounts are provided
    config = load_config()
    items = config["line_items"][args.client]
    missing = []
    for item in items:
        if item["type"] != "fixed" and item["pos"] not in amounts:
            missing.append(f"Pos {item['pos']} ({item['label']})")

    if missing:
        print("ERROR: Missing amounts for:")
        for m in missing:
            print(f"  - {m}")
        print("\nProvide via --pos3, --pos4, --pos5, --pos6 or --upwork-xlsx")
        sys.exit(1)

    # Generate
    output_path = generate_invoice(
        year=year,
        month=month,
        client_id=args.client,
        line_item_amounts=amounts,
        invoice_date=inv_date,
        output_dir=out_dir,
    )

    print(f"\nDone! Output: {output_path}")


if __name__ == "__main__":
    main()
