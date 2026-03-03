from __future__ import annotations

import hashlib
import re

import requests

from app.config import Settings


class LotteryCrawler:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.user_agent})

    def _request(self, url: str, **kwargs) -> requests.Response:
        return self.session.get(url, timeout=self.settings.request_timeout, **kwargs)

    def get_latest_draw_no(self) -> int:
        url = self.settings.lottery_base_url + self.settings.list_page
        resp = self._request(url)
        resp.raise_for_status()
        html = resp.text

        candidates = re.findall(r"\bdata-value\s*=\"(\d+)\"", html)
        if not candidates:
            m = re.search(r"id=\"opt_val\" value=\"(\d+)\"", html)
            if m:
                candidates = [m.group(1)]

        if not candidates:
            raise ValueError("Cannot parse latest draw number from result page")

        return max(map(int, candidates))

    def download_excel(self, start_no: int, end_no: int) -> tuple[bytes, str]:
        url = self.settings.lottery_base_url + self.settings.excel_endpoint
        params = {"srchStrLtEpsd": start_no, "srchEndLtEpsd": end_no}
        headers = {
            "Referer": self.settings.lottery_base_url + self.settings.list_page,
            "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/octet-stream, */*",
        }
        resp = self._request(url, params=params, headers=headers)
        # some environments redirect to error page if blocked; keep raw bytes for fallback path
        content = resp.content
        content_type = resp.headers.get("content-type", "").lower()

        if resp.status_code != 200:
            resp.raise_for_status()

        content_length = len(content)
        # fallback block: html moved page is always small and contains this marker
        if content_length < 256 and (b"document has been moved" in content or b"location" in content):
            raise ValueError("downloaded body is not a valid excel file")

        if "html" in content_type and content_length < 4_000:
            raise ValueError("downloaded body is likely not excel")

        file_hash = hashlib.sha256(content).hexdigest()
        return content, file_hash

    def fetch_draws_json(self, start_no: int, end_no: int) -> dict:
        url = self.settings.lottery_base_url + self.settings.json_endpoint
        params = {"srchStrLtEpsd": start_no, "srchEndLtEpsd": end_no}
        resp = self._request(url, params=params, headers={"Accept": "application/json"})
        resp.raise_for_status()
        return resp.json()
