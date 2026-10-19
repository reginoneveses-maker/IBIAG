"""Validate bounded CSV/XLSX content before materializing tables or writing records."""
import csv
import io
import re
import zipfile
from pathlib import PurePosixPath

import pandas as pd
from defusedxml.ElementTree import iterparse
from openpyxl import load_workbook
from fastapi import HTTPException
from upload_limits import read_import

MAX_ROWS = 10000
MAX_COLUMNS = 128
MAX_CELLS = 250000
MAX_CELL_CHARS = 32767
MAX_TEXT_CHARS = 8 * 1024 * 1024
MAX_XML_PART_BYTES = 16 * 1024 * 1024
MAX_XML_ELEMENTS = 1000000
MAX_XML_DEPTH = 64
MAX_STYLE_ELEMENTS = 10000
MAX_METADATA_ELEMENTS = 20000
MAX_SHARED_STRINGS = 100000
MAX_SHEETS = 20
MAX_HEADER_OFFSET = 2
INVALID_TABLE = "Planilha inválida. Confira o formato e os cabeçalhos; use CSV UTF-8 ou XLSX."
LIMIT_TABLE = "Planilha acima dos limites de processamento. Divida o arquivo em lotes menores."


def limit(condition):
    if condition:
        raise HTTPException(413, LIMIT_TABLE)


def _coordinate(value, max_row):
    match = re.fullmatch(r"([A-Za-z]{1,3})([1-9][0-9]{0,6})", value)
    if not match:
        raise ValueError()
    column = 0
    for char in match[1].upper():
        column = column * 26 + ord(char) - ord("A") + 1
    limit(column > MAX_COLUMNS or int(match[2]) > max_row)


def _xlsx_preflight(raw, header):
    """Inspect every XML part, not trusting worksheet dimensions or ZIP names."""
    elements = text_chars = cells = sheets = shared_strings = 0
    max_row = MAX_ROWS + header + 1
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        seen = set()
        for entry in archive.infolist():
            path = PurePosixPath(entry.filename)
            key = entry.filename.casefold()
            if key in seen or path.is_absolute() or ".." in path.parts or "\\" in entry.filename or entry.flag_bits & 1:
                raise ValueError()
            seen.add(key)
            if not key.endswith((".xml", ".rels")):
                continue
            limit(entry.file_size > MAX_XML_PART_BYTES)
            stack = []
            kind = None
            row_count = column_count = part_elements = 0
            string_chars = None
            with archive.open(entry) as source:
                for event, node in iterparse(source, events=("start", "end"),
                                            forbid_dtd=True, forbid_entities=True, forbid_external=True):
                    tag = node.tag.rsplit("}", 1)[-1]
                    if event == "start":
                        stack.append(node)
                        kind = kind or tag
                        elements += 1
                        part_elements += 1
                        limit(len(stack) > MAX_XML_DEPTH or elements > MAX_XML_ELEMENTS)
                        limit(kind == "styleSheet" and part_elements > MAX_STYLE_ELEMENTS)
                        limit(kind not in {"worksheet", "sst"} and part_elements > MAX_METADATA_ELEMENTS)
                        if tag in {"si", "is"}:
                            string_chars = 0
                        if tag == "si":
                            shared_strings += 1
                            limit(shared_strings > MAX_SHARED_STRINGS)
                        if tag == "sheet":
                            sheets += 1
                            limit(sheets > MAX_SHEETS)
                        if tag == "row":
                            row_count += 1
                            column_count = 0
                            index = node.get("r")
                            if index is not None and not re.fullmatch(r"[1-9][0-9]{0,6}", index):
                                raise ValueError()
                            limit(row_count > max_row or (index is not None and int(index) > max_row))
                        if tag == "c":
                            cells += 1
                            column_count += 1
                            limit(cells > MAX_CELLS or column_count > MAX_COLUMNS)
                            if node.get("r") is not None:
                                _coordinate(node.get("r"), max_row)
                    else:
                        content = node.text or ""
                        text_chars += len(content) + len(node.tail or "")
                        limit(text_chars > MAX_TEXT_CHARS or (tag in {"t", "v", "f"} and len(content) > MAX_CELL_CHARS))
                        if tag == "t" and string_chars is not None:
                            string_chars += len(content)
                            limit(string_chars > MAX_CELL_CHARS)
                        if tag in {"si", "is"}:
                            string_chars = None
                        stack.pop()
                        if stack:
                            stack[-1].remove(node)
                        node.clear()


def _csv_preflight(text, delimiter):
    """Count fields before csv.reader could allocate an adversarially wide row."""
    quoted = False
    field_start = True
    field_chars = columns = records = cells = 0
    columns = 1
    pending = False
    index = 0
    while index < len(text):
        char = text[index]
        if quoted:
            if char == '"':
                if index + 1 < len(text) and text[index + 1] == '"':
                    field_chars += 1
                    index += 1
                else:
                    quoted = False
            else:
                field_chars += 1
            pending = True
        elif char == delimiter:
            columns += 1
            field_chars = 0
            field_start = True
            pending = True
        elif char in "\r\n":
            records += 1
            cells += columns
            limit(records > MAX_ROWS + 1 or cells > MAX_CELLS)
            columns, field_chars, field_start, pending = 1, 0, True, False
            if char == "\r" and index + 1 < len(text) and text[index + 1] == "\n":
                index += 1
        elif char == '"' and field_start:
            quoted, field_start, pending = True, False, True
        else:
            field_chars += 1
            field_start, pending = False, True
        limit(columns > MAX_COLUMNS or field_chars > MAX_CELL_CHARS)
        index += 1
    if quoted:
        raise ValueError()
    if pending:
        records += 1
        cells += columns
    limit(records > MAX_ROWS + 1 or cells > MAX_CELLS)


def _frame(headers, rows):
    while rows and all(value is None or value == "" for value in rows[-1]):
        rows.pop()
    width = max([len(headers), *(len(row) for row in rows)])
    limit(len(rows) > MAX_ROWS or width > MAX_COLUMNS or (len(rows) + 1) * width > MAX_CELLS)
    names = [str(headers[i]).strip() if i < len(headers) and headers[i] is not None and str(headers[i]).strip()
             else f"Unnamed: {i}" for i in range(width)]
    if not names or len({name.casefold() for name in names}) != len(names):
        raise ValueError()
    return pd.DataFrame([list(row) + [None] * (width - len(row)) for row in rows], columns=names, dtype=object)


def _csv(raw):
    text = raw.decode("utf-8-sig")
    limit(len(text) > MAX_TEXT_CHARS)
    if "\x00" in text:
        raise ValueError()
    try:
        delimiter = csv.Sniffer().sniff(text[:8192], delimiters=",;\t").delimiter
    except csv.Error:
        first_line = text.split("\n", 1)[0]
        delimiter = max(",;\t", key=first_line.count)
    _csv_preflight(text, delimiter)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    rows = [row for row in reader if row]
    if not rows:
        raise ValueError()
    return _frame(rows[0], rows[1:])


def _xlsx(raw, sheet_name, header):
    _xlsx_preflight(raw, header)
    workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True, keep_links=False)
    try:
        sheet = workbook[sheet_name] if sheet_name is not None else workbook.worksheets[0]
        # Dimensions may overstate or understate real data; preflight checks
        # actual row/cell coordinates and the reader has a fixed column budget.
        sheet.reset_dimensions()
        rows = []
        for index, values in enumerate(sheet.iter_rows(max_col=MAX_COLUMNS + 1, values_only=True)):
            limit(index > MAX_ROWS + header)
            row = list(values)
            while row and row[-1] is None:
                row.pop()
            limit(len(row) > MAX_COLUMNS)
            limit(any(isinstance(value, str) and len(value) > MAX_CELL_CHARS for value in row))
            if index >= header:
                rows.append(row)
        if not rows:
            raise ValueError()
        return _frame(rows[0], rows[1:])
    finally:
        workbook.close()


async def read_table(file, *, sheet_name=None, header=0):
    raw = await read_import(file)
    try:
        if header < 0 or header > MAX_HEADER_OFFSET:
            raise ValueError()
        name = (file.filename or "").lower()
        if sheet_name is not None or name.endswith(".xlsx"):
            return _xlsx(raw, sheet_name, header)
        if name.endswith(".csv") and header == 0:
            return _csv(raw)
        raise ValueError()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, INVALID_TABLE) from None
