import os
import re
import pdfplumber
import pandas as pd
from docx import Document
from pypdf import PdfReader
from pptx import Presentation




def clean_cell(value):
    if value is None:
        return ""
    return str(value).strip()


def parse_number(value):
    if value is None:
        return None

    text = str(value)
    text = text.replace("$", "").replace(",", "").replace("%", "")
    text = text.replace("M", "").replace("B", "").strip()

    try:
        return float(text)
    except Exception:
        return None


def extract_numbers_from_text(text):
    pattern = r"[-+]?\$?\d[\d,]*(?:\.\d+)?%?"
    matches = re.findall(pattern, text)

    numbers = []

    for match in matches:
        value = parse_number(match)
        if value is not None:
            numbers.append({
                "raw": match,
                "value": value
            })

    return numbers


def dataframe_to_table(df, table_name="Table"):
    df = df.fillna("")
    headers = [str(col).strip() for col in df.columns]

    rows = []
    for _, row in df.iterrows():
        rows.append([clean_cell(v) for v in row.tolist()])

    return {
        "table_name": table_name,
        "headers": headers,
        "rows": rows
    }


def extract_docx(path):
    doc = Document(path)

    text_parts = []
    tables = []

    for para in doc.paragraphs:
        if para.text.strip():
            text_parts.append(para.text.strip())

    for index, table in enumerate(doc.tables):
        rows = []

        for row in table.rows:
            rows.append([clean_cell(cell.text) for cell in row.cells])

        if len(rows) > 1:
            headers = rows[0]
            body = rows[1:]

            tables.append({
                "table_name": f"DOCX Table {index + 1}",
                "headers": headers,
                "rows": body
            })

    text = "\n".join(text_parts)

    return text, tables


def extract_pdf(path):

    reader = PdfReader(path)

    text_parts = []
    tables = []

    with pdfplumber.open(path) as pdf:

        for page_num, page in enumerate(pdf.pages):

            page_text = page.extract_text() or ""

            if page_text.strip():
                text_parts.append(
                    f"--- Page {page_num+1} ---\n{page_text}"
                )

            page_tables = page.extract_tables()

            for idx, table in enumerate(page_tables):

                if len(table) < 2:
                    continue

                headers = [
                    clean_cell(x)
                    for x in table[0]
                ]

                rows = []

                for row in table[1:]:

                    rows.append(
                        [
                            clean_cell(cell)
                            for cell in row
                        ]
                    )

                tables.append(
                    {
                        "table_name":
                        f"PDF Page {page_num+1} Table {idx+1}",

                        "headers": headers,

                        "rows": rows
                    }
                )

    text = "\n\n".join(text_parts)

    if len(tables) == 0:
        tables = detect_text_tables(text)

    return text, tables

def extract_pptx(path):
    prs = Presentation(path)

    text_parts = []
    tables = []

    for slide_index, slide in enumerate(prs.slides):
        slide_text = []

        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                slide_text.append(shape.text.strip())

            if shape.has_table:
                table = shape.table
                rows = []

                for row in table.rows:
                    rows.append([clean_cell(cell.text) for cell in row.cells])

                if len(rows) > 1:
                    tables.append({
                        "table_name": f"PPTX Slide {slide_index + 1} Table",
                        "headers": rows[0],
                        "rows": rows[1:]
                    })

        if slide_text:
            text_parts.append(
                f"--- Slide {slide_index + 1} ---\n" + "\n".join(slide_text)
            )

    return "\n\n".join(text_parts), tables


def extract_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    return text, []


def extract_csv(path):
    df = pd.read_csv(path, skipinitialspace=True, on_bad_lines="skip")
    table = dataframe_to_table(df, "CSV Table")

    return df.to_string(index=False), [table]


def extract_excel(path):
    sheets = pd.read_excel(path, sheet_name=None)

    text_parts = []
    tables = []

    for sheet_name, df in sheets.items():
        table = dataframe_to_table(df, f"Excel Sheet: {sheet_name}")
        tables.append(table)
        text_parts.append(f"--- Sheet: {sheet_name} ---\n{df.to_string(index=False)}")

    return "\n\n".join(text_parts), tables


def build_chart_candidates_from_tables(tables):
    """
    Creates deterministic chart-ready data from extracted tables.
    This reduces hallucination because charts are created from real table values.
    """
    candidates = []

    for table in tables:
        headers = table.get("headers", [])
        rows = table.get("rows", [])

        if not headers or not rows:
            continue

        # Choose first column as label column
        label_col_index = 0

        for col_index in range(1, len(headers)):
            chart_data = []

            for row in rows:
                if len(row) <= col_index:
                    continue

                label = clean_cell(row[label_col_index])
                value = parse_number(row[col_index])

                if label and value is not None:
                    chart_data.append({
                        "label": label,
                        "value": value
                    })

            if len(chart_data) >= 2:
                chart_type = "line" if looks_like_time_series(chart_data) else "bar"

                candidates.append({
                    "title": f"{headers[col_index]} by {headers[label_col_index]}",
                    "chart_type": chart_type,
                    "source_table": table.get("table_name", ""),
                    "data": chart_data[:12]
                })

    return candidates[:20]


def looks_like_time_series(chart_data):

    labels = [
        str(x["label"]).lower()
        for x in chart_data
    ]

    months = {
        "jan","feb","mar","apr","may","jun",
        "jul","aug","sep","oct","nov","dec"
    }

    quarters = {
        "q1","q2","q3","q4"
    }

    hits = 0

    for l in labels:

        if l in months:
            hits += 1

        if l in quarters:
            hits += 1

        if re.match(r'fy\d+', l):
            hits += 1

        if re.match(r'20\d\d', l):
            hits += 1

    return hits >= 2


def extract_document_data(path):
    """
    Main function.

    Returns:
    {
      text,
      tables,
      numbers,
      chart_candidates,
      metric_cards
    }
    """
    ext = os.path.splitext(path)[1].lower()

    if ext == ".docx":
        text, tables = extract_docx(path)

    elif ext == ".pdf":
        text, tables = extract_pdf(path)

    elif ext == ".pptx":
        text, tables = extract_pptx(path)

    elif ext == ".txt":
        text, tables = extract_txt(path)

    elif ext == ".csv":
        text, tables = extract_csv(path)

    elif ext in [".xlsx", ".xls"]:
        text, tables = extract_excel(path)

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    numbers = extract_numbers_from_text(text)
    metric_cards = extract_metric_cards(text)
    chart_candidates = build_chart_candidates_from_tables(tables)
    sections = extract_sections(text)
    tables = normalize_single_column_tables(tables)

    return {
        "text": text,
        "tables": tables,
        "numbers": numbers,
        "metric_cards": metric_cards,
        "chart_candidates": chart_candidates,
        "sections": sections,
    
        # generic metadata
        "file_type": ext,
        "text_length": len(text),
        "table_count": len(tables),
        "metric_count": len(metric_cards),
        "chart_candidate_count": len(chart_candidates)
    }

def extract_metric_cards(text, max_cards=60):
    cards = []
    seen = set()

    for line in text.splitlines():
        line = line.strip()

        if len(line) < 5 or len(line) > 140:
            continue

        # Pattern 1: Label: Value
        match = re.match(
            r"^(.{3,70}?):\s*([$₹€£]?\d[\d,]*(?:\.\d+)?\s*[%A-Za-z/µμ₹$€£.-]*)\b",
            line
        )

        # Pattern 2: Label    Value   Optional Unit/Context
        if not match:
            parts = re.split(r"\s{2,}", line)

            if len(parts) >= 2:
                label = parts[0].strip()
                value = parts[1].strip()

                if parse_number(value) is not None:
                    key = (label.lower(), value.lower())

                    if key not in seen:
                        cards.append({
                            "label": label,
                            "value": value
                        })
                        seen.add(key)

                if len(cards) >= max_cards:
                    break

            continue

        label = match.group(1).strip()
        value = match.group(2).strip()

        if parse_number(value) is None:
            continue

        key = (label.lower(), value.lower())

        if key in seen:
            continue

        cards.append({
            "label": label,
            "value": value
        })
        seen.add(key)

        if len(cards) >= max_cards:
            break

    return cards
def extract_sections(text):

    sections = []

    pattern = re.findall(
        r'([A-Z][A-Za-z /&]{3,60})\n',
        text
    )

    for p in pattern:

        if len(p.split()) <= 8:

            sections.append(p)

    return list(set(sections))

def detect_text_tables(text):

    tables = []

    lines = text.split("\n")

    rows = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # split by multiple spaces
        parts = re.split(r'\s{2,}', line)

        if len(parts) >= 3:
            rows.append(parts)

    if len(rows) > 3:

        max_cols = max(len(r) for r in rows)

        headers = [f"Column {i+1}" for i in range(max_cols)]

        normalized_rows = []

        for r in rows:

            while len(r) < max_cols:
                r.append("")

            normalized_rows.append(r)

        tables.append(
            {
                "table_name": "Detected Text Table",
                "headers": headers,
                "rows": normalized_rows
            }
        )

    return tables
def normalize_single_column_tables(tables):
    """
    Generic structure normalizer.

    Converts one-column rows into variable-width rows without domain knowledge.
    It does not know medical, finance, ISO, research, units, or metrics.

    Example:
    "IRON 30 µg/dL 50 - 170"
    -> ["IRON", "30 µg/dL", "50 - 170"]

    "Revenue FY24 62.4 B North America"
    -> ["Revenue FY24", "62.4 B", "North America"]

    "Accuracy 97.3 % Test Dataset"
    -> ["Accuracy", "97.3 %", "Test Dataset"]
    """

    def is_number_token(token):
        return re.fullmatch(
            r"[-+]?\d[\d,]*(?:\.\d+)?%?",
            token
        ) is not None

    def is_numeric_connector(token):
        return token in ["-", "–", "—", "to", "±", "+/-"]

    def split_row_text(text):
        tokens = text.split()

        if len(tokens) < 2:
            return []

        chunks = []
        text_buffer = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            if is_number_token(token):
                if text_buffer:
                    chunks.append(" ".join(text_buffer).strip())
                    text_buffer = []

                numeric_chunk = [token]

                # Keep short immediate non-numeric token after number.
                # This is structural, not semantic.
                # Examples: %, M, B, mg/dL, km/h, ms, X, 10^3
                if i + 1 < len(tokens):
                    next_token = tokens[i + 1]

                    if (
                        not is_number_token(next_token)
                        and not is_numeric_connector(next_token)
                        and len(next_token) <= 12
                    ):
                        numeric_chunk.append(next_token)
                        i += 1

                # Keep simple numeric ranges: 50 - 170 / 1.0 to 3.0
                if i + 2 < len(tokens):
                    connector = tokens[i + 1]
                    next_number = tokens[i + 2]

                    if is_numeric_connector(connector) and is_number_token(next_number):
                        numeric_chunk.extend([connector, next_number])
                        i += 2

                        # Optional short token after range
                        if i + 1 < len(tokens):
                            after_range = tokens[i + 1]

                            if (
                                not is_number_token(after_range)
                                and not is_numeric_connector(after_range)
                                and len(after_range) <= 12
                            ):
                                numeric_chunk.append(after_range)
                                i += 1

                chunks.append(" ".join(numeric_chunk).strip())

            else:
                text_buffer.append(token)

            i += 1

        if text_buffer:
            chunks.append(" ".join(text_buffer).strip())

        return [chunk for chunk in chunks if chunk]

    normalized_tables = []

    for table in tables:
        headers = table.get("headers", [])
        rows = table.get("rows", [])

        if not rows:
            normalized_tables.append(table)
            continue

        is_single_column = (
            len(headers) == 1
            or all(len(row) == 1 for row in rows)
        )

        if not is_single_column:
            normalized_tables.append(table)
            continue

        structured_rows = []

        for row in rows:
            if not row:
                continue

            text = clean_cell(row[0])

            if not text:
                continue

            parts = split_row_text(text)

            if len(parts) >= 2:
                structured_rows.append(parts)

        if len(structured_rows) < 2:
            normalized_tables.append(table)
            continue

        max_cols = max(len(row) for row in structured_rows)

        padded_rows = []

        for row in structured_rows:
            while len(row) < max_cols:
                row.append("")
            padded_rows.append(row)

        normalized_tables.append({
            "table_name": table.get("table_name", "Normalized Table"),
            "headers": [f"Column {i + 1}" for i in range(max_cols)],
            "rows": padded_rows
        })

    return normalized_tables