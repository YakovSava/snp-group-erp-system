import json
import math
import re

from sqlalchemy.orm import Session

from .. import llm_client
from . import rates as rates_module

ROUNDING_STEP = {
    "AMD": 100,
    "RUB": 100,
    "USD": 1,
    "EUR": 1,
}


def round_up(amount: float, currency: str) -> float:
    """Always rounds UP to the nearest step for the target currency —
    this is a fixed business rule, never left to the model's arithmetic.
    """
    step = ROUNDING_STEP.get(currency.upper(), 1)
    return math.ceil(amount / step) * step


class NoRateAvailable(Exception):
    pass


def convert_amount(db: Session, amount: float, from_currency: str, to_currency: str) -> tuple[float, float, str]:
    """Returns (rounded_converted_amount, rate_used, source)."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return round_up(amount, to_currency), 1.0, "identity"

    if from_currency == "AMD" or to_currency == "AMD":
        record = rates_module.get_latest_rate(db, from_currency, to_currency)
        if record is None:
            raise NoRateAvailable(f"No cached rate for {from_currency}->{to_currency}")
        rate, source = float(record.rate), record.source
    else:
        # Pivot through AMD for pairs that don't directly involve it (e.g. RUB->USD).
        to_amd = rates_module.get_latest_rate(db, from_currency, "AMD")
        from_amd = rates_module.get_latest_rate(db, "AMD", to_currency)
        if to_amd is None or from_amd is None:
            raise NoRateAvailable(f"No cached rate path for {from_currency}->{to_currency}")
        rate = float(to_amd.rate) * float(from_amd.rate)
        source = f"{to_amd.source}+{from_amd.source}"

    return round_up(amount * rate, to_currency), rate, source


_EXTRACTION_PROMPT = (
    "Найди все упоминания денежных сумм в тексте ниже и верни ТОЛЬКО JSON-массив "
    'вида [{"amount": 1000, "currency": "AMD"}, ...] без пояснений. '
    "Используй коды валют AMD, RUB, USD, EUR (драм/դրամ -> AMD, руб/₽ -> RUB, "
    "$/долларов -> USD, €/евро -> EUR). Если сумм нет, верни []."
    "\n\nТекст:\n"
)


def extract_money_mentions(text: str) -> list[dict]:
    """Uses the LLM only to *find* amounts in free text — never to compute
    the conversion itself. Falls back to an empty list on any parsing
    failure so a flaky extraction never breaks the calling pipeline.
    """
    raw = llm_client.raw_completion(
        [{"role": "user", "content": _EXTRACTION_PROMPT + text}],
    )
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return [item for item in parsed if isinstance(item, dict) and "amount" in item and "currency" in item]


def annotate_amd_amounts_with_usd(db: Session, text: str) -> str:
    """Appends a parenthetical USD equivalent after every AMD amount found
    in the text, e.g. "10 000 դրամ" -> "10 000 դրամ (~28 $)". Used for the
    EN post translation, aimed at an international audience.
    """
    mentions = [m for m in extract_money_mentions(text) if m.get("currency", "").upper() == "AMD"]
    result = text
    for mention in mentions:
        try:
            usd_amount, _, _ = convert_amount(db, float(mention["amount"]), "AMD", "USD")
        except NoRateAvailable:
            continue
        original = str(mention["amount"])
        if original in result:
            result = result.replace(original, f"{original} (~{int(usd_amount)} $)", 1)
    return result
