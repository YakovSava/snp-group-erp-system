import logging

from apscheduler.schedulers.background import BackgroundScheduler

from ..db import SessionLocal
from . import rates as rates_module

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler()


def _refresh_job():
    db = SessionLocal()
    try:
        source = rates_module.refresh_rates(db)
        logger.info("Currency rates refreshed from %s", source)
    except Exception:
        logger.exception("Currency rate refresh failed")
    finally:
        db.close()


def start():
    _refresh_job()  # populate the cache immediately on startup
    _scheduler.add_job(_refresh_job, "interval", hours=1, id="refresh_currency_rates", replace_existing=True)
    _scheduler.start()


def shutdown():
    _scheduler.shutdown(wait=False)
