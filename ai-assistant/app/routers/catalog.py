import json
import re

from fastapi import APIRouter, Depends

from .. import llm_client
from ..deps import require_service_token
from ..schemas import CatalogMappingRequest, CatalogMappingResponse

router = APIRouter(prefix="/v1", dependencies=[Depends(require_service_token)])

# "ignore" is for genuinely empty/decorative columns (e.g. a row-number
# column) — anything the model isn't sure about should default to "comment"
# instead, per the brief: nothing that might be real data should be silently
# dropped.
CATALOG_COLUMN_FIELDS = [
    "title",
    "article",
    "amount_amd",
    "amount_rub",
    "amount_usd",
    "description",
    "supplier",
    "comment",
    "ignore",
]

MAPPING_PROMPT = (
    "Это предпросмотр прайс-листа поставщика (Excel), который сотрудник хочет "
    "импортировать в каталог товаров компании SNP. Единого стандарта оформления "
    "таких файлов нет — структура каждый раз своя. Определи, что означает "
    "каждый столбец.\n\n"
    "Столбцы (индекс с 0, заголовок, несколько примеров значений):\n{columns_block}\n\n"
    "Для каждого столбца выбери ОДНО значение из списка: "
    f"{', '.join(CATALOG_COLUMN_FIELDS)}.\n"
    "title — название/заголовок товара. article — артикул (обычно короткий код "
    "из букв/цифр, не обязательно числовой). amount_amd/amount_rub/amount_usd — "
    "цена в драмах/рублях/долларах (ищи по заголовку: драм/AMD/֏, руб/₽/RUB, "
    "$/USD/долл; а также по характерным числам). description — текстовое "
    "описание товара. supplier — производитель/поставщик/страна. comment — ЛЮБОЙ "
    "столбец с данными, который не относится к перечисленному выше (количество, "
    "себестоимость, код ТН ВЭД и т.п.) — если не уверен, выбирай comment, а не "
    "ignore. ignore — только для пустых или чисто технических столбцов (например "
    "порядковый номер строки без иной информации).\n\n"
    "Если в файле нет столбца с ценой в рублях и/или в долларах, но ЕСТЬ столбец "
    "с ценой в драмах, укажи разумный процент наценки для пересчёта из драм "
    "(обычно в таких прайс-листах рубли считают как драмы +10%, доллары — как "
    "драмы +15%, но если видишь в примерах данные, по которым можно вычислить "
    "фактический процент — используй его). Если столбец с ценой в рублях/"
    "долларах уже есть — markup-поля для него оставь null.\n\n"
    'Верни ТОЛЬКО JSON без пояснений, строго в виде:\n'
    '{{"column_fields": ["...", ...], "amount_rub_markup_percent": число_или_null, '
    '"amount_usd_markup_percent": число_или_null, "notes": "краткое пояснение на '
    'русском, что ты определил и почему"}}\n'
    "column_fields должен содержать ровно столько элементов, сколько столбцов "
    "перечислено выше, в том же порядке."
)


def _format_columns_block(headers: list[str], sample_rows: list[list[str]]) -> str:
    lines = []
    for idx, header in enumerate(headers):
        examples = [row[idx] for row in sample_rows if idx < len(row) and row[idx]][:4]
        lines.append(f"[{idx}] заголовок: {header or '(пусто)'}; примеры: {examples}")
    return "\n".join(lines)


def _parse_mapping_json(raw: str, column_count: int) -> CatalogMappingResponse:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    fallback = CatalogMappingResponse(column_fields=["comment"] * column_count)
    if not match:
        return fallback
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return fallback

    column_fields = parsed.get("column_fields")
    if not isinstance(column_fields, list) or len(column_fields) != column_count:
        return fallback
    column_fields = [f if f in CATALOG_COLUMN_FIELDS else "comment" for f in column_fields]

    def _as_float(value):
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    return CatalogMappingResponse(
        column_fields=column_fields,
        amount_rub_markup_percent=_as_float(parsed.get("amount_rub_markup_percent")),
        amount_usd_markup_percent=_as_float(parsed.get("amount_usd_markup_percent")),
        notes=str(parsed.get("notes") or ""),
    )


@router.post("/catalog/import-mapping", response_model=CatalogMappingResponse)
def suggest_catalog_mapping(payload: CatalogMappingRequest):
    """Suggests which catalog field each column of an uploaded price-list
    maps to, from its header + a handful of sample rows. This is only ever a
    starting point — apps.catalog in auto-smm shows the suggestion to the
    employee on a review screen before anything is actually imported, so
    getting a column wrong here costs a click to fix, not a bad price.
    """
    if not payload.headers:
        return CatalogMappingResponse(column_fields=[])

    prompt = MAPPING_PROMPT.format(
        columns_block=_format_columns_block(payload.headers, payload.sample_rows)
    )
    raw = llm_client.raw_completion([{"role": "user", "content": prompt}])
    return _parse_mapping_json(raw, len(payload.headers))
