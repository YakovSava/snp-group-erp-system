"""Reading/writing the catalog's Excel import & export files.

Column-mapping guesses come from the AI (apps.core.ai_client.suggest_catalog_
mapping); everything here is plain deterministic parsing and arithmetic —
never trust the model to do the actual row-by-row extraction or price math,
only to point at which column is which (same split of responsibility as
apps.posts' currency conversion: AI finds things, code computes things).
"""
import io
from decimal import Decimal, InvalidOperation

import openpyxl
from django.utils.translation import gettext_lazy as _

PREVIEW_SAMPLE_ROWS = 5
# How many leading rows we're willing to read through looking for the first
# non-blank one (the real header) — hand-maintained price lists sometimes
# have a blank row or a merged title/logo row above the actual header.
HEADER_SEARCH_ROWS = 20

# Fields a column can be mapped to that hold exactly one value per row.
# "comment" is deliberately excluded: multiple columns can all feed it.
SINGLE_VALUE_FIELDS = [
    "title",
    "article",
    "amount_amd",
    "amount_rub",
    "amount_usd",
    "description",
    "supplier",
]

EXPORT_HEADERS = [
    ("title", _("Заголовок")),
    ("article", _("Артикул")),
    ("amount_amd", _("Цена, AMD")),
    ("amount_rub", _("Цена, RUB")),
    ("amount_usd", _("Цена, USD")),
    ("description", _("Описание")),
    ("supplier", _("Поставщик")),
    ("comment", _("Комментарии")),
]


def _cell_to_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_blank_row(row: list[str]) -> bool:
    return not any(row)


def _split_header(rows: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    """The header is the first non-blank row, not necessarily row 1 — a
    blank spacer row, or a merged title/logo row above the real header, is
    common enough in hand-maintained price lists that assuming row 1 is
    always the header silently pulled the real header into the data rows.
    """
    for idx, row in enumerate(rows):
        if not _is_blank_row(row):
            return row, rows[idx + 1:]
    return [], []


def read_preview(file_obj) -> tuple[list[str], list[list[str]]]:
    """Returns (headers, sample_rows) from the first sheet's header row (the
    first non-blank row) and up to PREVIEW_SAMPLE_ROWS rows after it — just
    enough for the AI to guess the column mapping from.
    """
    workbook = openpyxl.load_workbook(file_obj, data_only=True, read_only=True)
    try:
        sheet = workbook.worksheets[0]
        rows = []
        for row in sheet.iter_rows(values_only=True):
            rows.append([_cell_to_str(c) for c in row])
            if len(rows) >= HEADER_SEARCH_ROWS:
                break
    finally:
        workbook.close()

    headers, data_rows = _split_header(rows)
    return headers, data_rows[:PREVIEW_SAMPLE_ROWS]


def read_data_rows(file_obj) -> list[list[str]]:
    """All rows after the header row (the first non-blank row) of the first sheet."""
    workbook = openpyxl.load_workbook(file_obj, data_only=True, read_only=True)
    try:
        sheet = workbook.worksheets[0]
        rows = [[_cell_to_str(c) for c in row] for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()
    _, data_rows = _split_header(rows)
    return data_rows


def _to_decimal(text: str) -> Decimal | None:
    if not text:
        return None
    cleaned = text.replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def apply_markup(amount: Decimal | None, percent) -> Decimal | None:
    if amount is None or percent in (None, ""):
        return None
    try:
        percent = Decimal(str(percent))
    except InvalidOperation:
        return None
    return (amount * (Decimal("1") + percent / Decimal("100"))).quantize(Decimal("0.01"))


def parse_rows(
    data_rows: list[list[str]],
    headers: list[str],
    column_fields: list[str],
    amount_rub_markup_percent=None,
    amount_usd_markup_percent=None,
) -> list[dict]:
    """column_fields[i] says what field column i maps to (one of
    SINGLE_VALUE_FIELDS, "comment", or "ignore") — see CatalogMappingForm.
    Rows with neither a title nor an article are skipped (blank spacer rows,
    common in hand-maintained price lists).
    """
    field_to_column = {}
    comment_columns = []
    for idx, field in enumerate(column_fields):
        if field == "comment":
            comment_columns.append(idx)
        elif field in SINGLE_VALUE_FIELDS:
            field_to_column.setdefault(field, idx)

    items = []
    for row in data_rows:
        def cell(idx):
            return row[idx] if idx is not None and idx < len(row) else ""

        title = cell(field_to_column.get("title"))
        article = cell(field_to_column.get("article"))
        if not title and not article:
            continue

        amount_amd = _to_decimal(cell(field_to_column.get("amount_amd")))
        amount_rub = _to_decimal(cell(field_to_column.get("amount_rub")))
        amount_usd = _to_decimal(cell(field_to_column.get("amount_usd")))
        if amount_rub is None:
            amount_rub = apply_markup(amount_amd, amount_rub_markup_percent)
        if amount_usd is None:
            amount_usd = apply_markup(amount_amd, amount_usd_markup_percent)

        comment_parts = []
        for idx in comment_columns:
            value = cell(idx)
            if value:
                label = headers[idx] if idx < len(headers) and headers[idx] else f"col {idx}"
                comment_parts.append(f"{label}: {value}")

        items.append({
            "title": title,
            "article": article,
            "amount_amd": amount_amd,
            "amount_rub": amount_rub,
            "amount_usd": amount_usd,
            "description": cell(field_to_column.get("description")),
            "supplier": cell(field_to_column.get("supplier")),
            "comment": " | ".join(comment_parts),
        })
    return items


def deduplicate_items(items: list[dict]) -> tuple[list[dict], int]:
    """Collapses rows sharing the same article (case/whitespace-insensitive —
    articles aren't a normalized format) into one, keeping the last
    occurrence: in a hand-maintained price list a correction appended
    further down is the common real-world case. Rows with no article can't
    be matched this way and are always kept as-is.

    Returns (deduplicated_items, how_many_duplicate_rows_were_merged).
    """
    by_article: dict[str, dict] = {}
    order: list[str] = []
    unkeyed: list[dict] = []
    duplicates = 0

    for item in items:
        article = (item.get("article") or "").strip()
        if not article:
            unkeyed.append(item)
            continue
        key = article.casefold()
        if key in by_article:
            duplicates += 1
        else:
            order.append(key)
        by_article[key] = item

    deduped = [by_article[key] for key in order] + unkeyed
    return deduped, duplicates


def build_export_workbook(items) -> bytes:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = str(_("Каталог"))[:31]
    sheet.append([str(label) for _, label in EXPORT_HEADERS])
    for item in items:
        sheet.append([getattr(item, field) for field, _ in EXPORT_HEADERS])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
