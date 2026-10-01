import datetime
import xml.etree.ElementTree as ET

import httpx
from sqlalchemy.orm import Session

from ..models import CurrencyRate

CBA_SOAP_URL = "http://api.cba.am/exchangerates.asmx"
CBA_NAMESPACE = "http://www.cba.am/"
FALLBACK_URL = "https://open.er-api.com/v6/latest/USD"

TRACKED_CURRENCIES = ["USD", "EUR", "RUB"]

SOAP_ENVELOPE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ExchangeRatesLatest xmlns="http://www.cba.am/" />
  </soap:Body>
</soap:Envelope>"""


def _local_tag(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _fetch_from_cba() -> dict[str, float]:
    """Returns {ISO: amd_per_unit}, derived from CBA's Rate/Amount pair —
    rates are often quoted per N units (e.g. per 100 RUB), not per 1.
    """
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f"{CBA_NAMESPACE}ExchangeRatesLatest",
    }
    response = httpx.post(CBA_SOAP_URL, content=SOAP_ENVELOPE, headers=headers, timeout=10.0)
    response.raise_for_status()
    root = ET.fromstring(response.text)

    rates: dict[str, float] = {}
    for elem in root.iter():
        if _local_tag(elem.tag) != "ExchangeRate":
            continue
        values = {_local_tag(child.tag): child.text for child in elem}
        iso = values.get("ISO")
        amount = float(values.get("Amount") or 1)
        rate = float(values.get("Rate") or 0)
        if iso and rate:
            rates[iso] = rate / amount
    if not rates:
        raise ValueError("CBA response contained no ExchangeRate entries")
    return rates


def _fetch_from_fallback() -> dict[str, float]:
    """Returns {ISO: amd_per_unit}, derived from a free USD-based rate table."""
    response = httpx.get(FALLBACK_URL, timeout=10.0)
    response.raise_for_status()
    data = response.json()
    usd_rates = data["rates"]
    amd_per_usd = usd_rates["AMD"]
    result: dict[str, float] = {}
    for iso in TRACKED_CURRENCIES:
        if iso == "USD":
            result["USD"] = amd_per_usd
        elif iso in usd_rates:
            result[iso] = amd_per_usd / usd_rates[iso]
    return result


def refresh_rates(db: Session) -> str:
    """Fetches fresh rates (CBA first, free fallback on any failure) and
    caches both directions (ISO->AMD and AMD->ISO) for each tracked currency.
    Returns the source actually used.
    """
    try:
        amd_per_unit = _fetch_from_cba()
        source = "cba.am"
    except Exception:
        amd_per_unit = _fetch_from_fallback()
        source = "open.er-api.com"

    now = datetime.datetime.now(datetime.timezone.utc)
    for iso in TRACKED_CURRENCIES:
        if iso not in amd_per_unit or not amd_per_unit[iso]:
            continue
        rate_to_amd = amd_per_unit[iso]
        db.add(CurrencyRate(base_code=iso, quote_code="AMD", rate=rate_to_amd, source=source, fetched_at=now))
        db.add(CurrencyRate(base_code="AMD", quote_code=iso, rate=1 / rate_to_amd, source=source, fetched_at=now))
    db.commit()
    return source


def get_latest_rate(db: Session, base_code: str, quote_code: str) -> CurrencyRate | None:
    return (
        db.query(CurrencyRate)
        .filter(CurrencyRate.base_code == base_code, CurrencyRate.quote_code == quote_code)
        .order_by(CurrencyRate.fetched_at.desc())
        .first()
    )
