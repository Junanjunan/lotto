from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_path: str = "data/lotto.db"
    lottery_base_url: str = "https://www.dhlottery.co.kr"
    list_page: str = "/lt645/result"
    excel_endpoint: str = "/lt645/excelDown.do"
    json_endpoint: str = "/lt645/selectPstLt645Info.do"
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    request_timeout: int = 30
