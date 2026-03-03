from __future__ import annotations

import io
from typing import Iterable

from openpyxl import load_workbook

from app.models import Draw


def _to_int(v) -> int | None:
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        if not s:
            return None
        try:
            return int(float(s))
        except ValueError:
            return None
    return None


def _find_draw_fields(row: tuple) -> tuple[int, str, list[int], int] | None:
    nums = [_to_int(v) for v in row if _to_int(v) is not None]
    nums = [n for n in nums if n is not None]

    # common style: [1213, 20260228, 5, 11, ...]
    if len(nums) >= 8 and 1 <= nums[0] <= 10000:
        draw_no = nums[0]
        # date is optional, numbers may start after one index
        candidate = nums[1:9]
        # if draw date exists as 8-digit date, shift accordingly
        if len(candidate) >= 8 and candidate[0] > 20000000:
            candidate = candidate[1:8]

        if len(candidate) >= 7:
            main = candidate[:6]
            bonus = candidate[6]
            if _valid_lotto_numbers(main, bonus):
                return draw_no, "", sorted(main), bonus

    # fallback pattern where first seven numbers are draw+6 nums+bonus
    for i in range(min(3, len(nums) - 7)):
        draw_no = nums[i]
        if not (1 <= draw_no <= 10000):
            continue
        main = nums[i + 1 : i + 7]
        bonus = nums[i + 7]
        if len(main) < 6:
            continue
        if _valid_lotto_numbers(main, bonus):
            return draw_no, "", sorted(main), bonus

    return None


def _valid_lotto_numbers(main: Iterable[int], bonus: int) -> bool:
    main_list = list(main)
    if len(main_list) != 6:
        return False
    if len(set(main_list)) != 6:
        return False
    if not all(1 <= n <= 45 for n in main_list):
        return False
    if not (1 <= bonus <= 45):
        return False
    return True


def parse_excel_draws(content: bytes) -> list[Draw]:
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = ws.iter_rows(values_only=True)

    # skip header rows until values appear
    parsed: list[Draw] = []

    for raw in rows:
        if all(v is None for v in raw):
            continue
        found = _find_draw_fields(raw)
        if not found:
            continue

        draw_no, draw_date, main_nums, bonus = found
        parsed.append(Draw(draw_no=draw_no, draw_date=str(draw_date or ""), numbers=list(main_nums), bonus=bonus))

    return parsed
