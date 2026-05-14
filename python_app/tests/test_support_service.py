"""Unit tests for support_service (GETSCODE / GETCOMPY / CRDTAGY / ABNDPROC)."""

from __future__ import annotations

import logging
import random

from app.services.support_service import (
    AbendInfo,
    abend_handler,
    credit_score_check,
    get_company_name,
    get_sort_code,
)


def test_get_sort_code_matches_cobol_sortcode_cpy():
    assert get_sort_code() == "987654"


def test_get_company_name_matches_cobol_getcompy_cbl():
    assert get_company_name() == "CICS Bank Sample Application"


def test_credit_score_check_returns_value_in_range():
    rng = random.Random(42)
    for _ in range(20):
        score = credit_score_check(simulate_delay=False, rng=rng)
        assert 1 <= score <= 999


def test_abend_handler_logs_error(caplog):
    caplog.set_level(logging.ERROR, logger="cbsa.abend")
    abend_handler(
        AbendInfo(program="TEST", code="ABCD", message="boom", sqlcode=-803)
    )
    assert "TEST" in caplog.text
    assert "ABCD" in caplog.text
    assert "boom" in caplog.text
