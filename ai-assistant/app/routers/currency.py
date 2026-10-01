from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..currency.convert import NoRateAvailable, convert_amount, extract_money_mentions
from ..currency.rates import TRACKED_CURRENCIES, get_latest_rate
from ..db import get_db
from ..deps import require_service_token
from ..schemas import ConvertCurrencyRequest, ConvertCurrencyResponse, ConvertedAmount

router = APIRouter(prefix="/v1", dependencies=[Depends(require_service_token)])


def _convert_one(db: Session, amount: float, from_currency: str, to_currency: str) -> ConvertedAmount:
    converted, rate, source = convert_amount(db, amount, from_currency, to_currency)
    return ConvertedAmount(
        original_amount=amount,
        original_currency=from_currency.upper(),
        converted_amount=converted,
        converted_currency=to_currency.upper(),
        rate_used=rate,
        rate_source=source,
    )


@router.post("/convert-currency", response_model=ConvertCurrencyResponse)
def convert_currency(payload: ConvertCurrencyRequest, db: Session = Depends(get_db)):
    if payload.amount is not None:
        if not payload.from_currency or not payload.to_currency:
            raise HTTPException(status_code=400, detail="from_currency and to_currency are required with amount")
        try:
            result = _convert_one(db, payload.amount, payload.from_currency, payload.to_currency)
        except NoRateAvailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return ConvertCurrencyResponse(result=result)

    if payload.text:
        mentions = extract_money_mentions(payload.text)
        detected = []
        rewritten = payload.text
        for mention in mentions:
            from_currency = str(mention["currency"]).upper()
            to_currency = (payload.to_currency or "AMD").upper()
            if from_currency == to_currency:
                continue
            try:
                converted = _convert_one(db, float(mention["amount"]), from_currency, to_currency)
            except NoRateAvailable:
                continue
            detected.append(converted)
            original_str = str(mention["amount"])
            if original_str in rewritten:
                rewritten = rewritten.replace(
                    original_str,
                    f"{original_str} {from_currency} (~{int(converted.converted_amount)} {to_currency})",
                    1,
                )
        return ConvertCurrencyResponse(detected=detected, rewritten_text=rewritten)

    raise HTTPException(status_code=400, detail="Either amount or text must be provided")


@router.get("/currency/rates")
def latest_rates(db: Session = Depends(get_db)):
    rates = {}
    for iso in TRACKED_CURRENCIES:
        record = get_latest_rate(db, iso, "AMD")
        if record:
            rates[f"{iso}->AMD"] = {"rate": float(record.rate), "source": record.source, "fetched_at": record.fetched_at}
    return rates
