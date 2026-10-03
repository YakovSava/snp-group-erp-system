from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_token: str = "change-me"

    # Facebook (Meta Graph API) — a Page and a Page access token with
    # pages_manage_posts. Posting to a personal profile isn't supported by
    # the Graph API, only to Pages.
    facebook_page_id: str = ""
    facebook_page_access_token: str = ""

    # Instagram (Meta Graph API, via the linked IG Business Account).
    # The access token is usually the same Page token as Facebook's, since
    # Meta unifies Page/IG permissions under one token — kept as a separate
    # setting so the two can still be rotated independently.
    instagram_business_account_id: str = ""
    instagram_access_token: str = ""

    # Threads (Meta's separate Threads Graph API, its own user id + token).
    threads_user_id: str = ""
    threads_access_token: str = ""

    # Telegram Bot API.
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # MAX messenger Bot API (dev.max.ru) — Telegram-Bot-API-shaped.
    max_bot_token: str = ""
    max_chat_id: str = ""

    # X (Twitter) API v2 — posting requires signed OAuth1 user-context,
    # not just a bearer token.
    x_api_key: str = ""
    x_api_secret: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""

    # VK API — a community (group) access token with wall permission.
    vk_access_token: str = ""
    vk_group_id: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
