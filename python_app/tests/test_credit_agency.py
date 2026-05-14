"""Unit tests for the async credit-agency fan-out (FR-04).

Covers the Python port of ``CRDTAGY1..5.cbl`` and the ``CREDIT-CHECK``
section of ``CRECUST.cbl``:

* Successful 5-way fan-out averages the per-agency scores.
* ``CBSA_CREDIT_AGENCY_SEED`` makes the score deterministic.
* When all agencies time out we raise ``CreditAgencyTimeoutError``.
* When only some agencies time out we average over the survivors.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from app.api.dependencies import _STATUS_BY_ERROR, cbsa_error_to_http
from app.services.credit_agency_client import (
    SEED_ENV_VAR,
    CreditAgencyClient,
)
from app.services.errors import CreditAgencyTimeoutError
from app.services.support_service import (
    CREDIT_AGENCY_TIMEOUT_SECONDS,
    credit_score_check,
    credit_score_check_async,
)


@pytest.mark.asyncio
async def test_all_five_agencies_return_and_score_is_averaged() -> None:
    """Every agency must contribute to the averaged score."""
    client = CreditAgencyClient(seed=123)
    expected = [
        await client.call_agency_1(simulate_delay=False),
        await client.call_agency_2(simulate_delay=False),
        await client.call_agency_3(simulate_delay=False),
        await client.call_agency_4(simulate_delay=False),
        await client.call_agency_5(simulate_delay=False),
    ]
    # Re-seed so the fan-out sees the same per-agency RNG state.
    fresh = CreditAgencyClient(seed=123)
    averaged = await credit_score_check_async(simulate_delay=False, client=fresh)
    assert averaged == sum(expected) // len(expected)
    assert 0 <= averaged <= 999


@pytest.mark.asyncio
async def test_seed_env_var_makes_score_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two runs with the same ``CBSA_CREDIT_AGENCY_SEED`` yield the same score."""
    monkeypatch.setenv(SEED_ENV_VAR, "42")
    first = await credit_score_check_async(simulate_delay=False)
    second = await credit_score_check_async(simulate_delay=False)
    assert first == second


@pytest.mark.asyncio
async def test_partial_timeout_averages_over_survivors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If one agency hangs we still average over the four that returned."""
    client = CreditAgencyClient(seed=7)

    async def hang(*, simulate_delay: bool = True) -> int:
        await asyncio.sleep(CREDIT_AGENCY_TIMEOUT_SECONDS + 2)
        return 0

    monkeypatch.setattr(client, "call_agency_3", hang)

    score = await credit_score_check_async(simulate_delay=False, client=client)
    assert 0 <= score <= 999

    # The survivors are agencies 1, 2, 4, 5 (under the same seed=7).
    reference = CreditAgencyClient(seed=7)
    expected = [
        await reference.call_agency_1(simulate_delay=False),
        await reference.call_agency_2(simulate_delay=False),
        await reference.call_agency_4(simulate_delay=False),
        await reference.call_agency_5(simulate_delay=False),
    ]
    assert score == sum(expected) // len(expected)


@pytest.mark.asyncio
async def test_total_timeout_raises_credit_agency_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When every agency exceeds the 3-second window, we raise."""
    client = CreditAgencyClient(seed=1)

    async def hang(*, simulate_delay: bool = True) -> int:
        await asyncio.sleep(CREDIT_AGENCY_TIMEOUT_SECONDS + 2)
        return 999

    for attr in (
        "call_agency_1",
        "call_agency_2",
        "call_agency_3",
        "call_agency_4",
        "call_agency_5",
    ):
        monkeypatch.setattr(client, attr, hang)

    with pytest.raises(CreditAgencyTimeoutError) as excinfo:
        await credit_score_check_async(simulate_delay=False, client=client)
    assert excinfo.value.fail_code == "T"


@pytest.mark.asyncio
async def test_partial_timeout_with_only_one_survivor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One survivor is enough — its score *is* the average."""
    client = CreditAgencyClient(seed=99)

    async def hang(*, simulate_delay: bool = True) -> int:
        await asyncio.sleep(CREDIT_AGENCY_TIMEOUT_SECONDS + 2)
        return 0

    for attr in (
        "call_agency_2",
        "call_agency_3",
        "call_agency_4",
        "call_agency_5",
    ):
        monkeypatch.setattr(client, attr, hang)

    score = await credit_score_check_async(simulate_delay=False, client=client)
    reference = CreditAgencyClient(seed=99)
    expected = await reference.call_agency_1(simulate_delay=False)
    assert score == expected


def test_invalid_seed_env_var_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-integer ``CBSA_CREDIT_AGENCY_SEED`` falls back to system entropy."""
    monkeypatch.setenv(SEED_ENV_VAR, "not-an-int")
    client = CreditAgencyClient()
    score = asyncio.run(client.call_agency_1(simulate_delay=False))
    assert 0 <= score <= 999


def test_sync_shim_drives_async_fan_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``credit_score_check()`` with no rng arg drives the async path."""
    monkeypatch.setenv(SEED_ENV_VAR, "1234")
    score = credit_score_check(simulate_delay=False)
    assert 0 <= score <= 999


def test_base_urls_validation() -> None:
    """The HTTP-mode client validates ``base_urls`` length up front."""
    with pytest.raises(ValueError):
        CreditAgencyClient(mode="http", base_urls=["http://x"] * 4)


@pytest.mark.asyncio
async def test_http_mode_uses_injected_client() -> None:
    """``mode='http'`` issues a GET request against the per-agency URL."""
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, json={"score": 750})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = CreditAgencyClient(
            mode="http",
            base_urls=[f"http://agency-{i}/score" for i in range(1, 6)],
            http_client=http_client,
        )
        score = await client.call_agency_1(simulate_delay=False)
    assert score == 750
    assert seen_urls == ["http://agency-1/score"]


@pytest.mark.asyncio
async def test_seed_via_env_matches_seed_via_kwarg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``CBSA_CREDIT_AGENCY_SEED`` and the ``seed=`` kwarg drive the same RNG."""
    monkeypatch.delenv(SEED_ENV_VAR, raising=False)
    explicit = CreditAgencyClient(seed=5)

    monkeypatch.setenv(SEED_ENV_VAR, "5")
    from_env = CreditAgencyClient()

    assert await explicit.call_agency_1(
        simulate_delay=False
    ) == await from_env.call_agency_1(simulate_delay=False)


def test_credit_agency_timeout_error_maps_to_504() -> None:
    """The new error is wired into the FastAPI error map (HTTP 504)."""
    err = CreditAgencyTimeoutError("boom")
    assert _STATUS_BY_ERROR[CreditAgencyTimeoutError] == 504
    http_exc = cbsa_error_to_http(err)
    assert http_exc.status_code == 504
    assert http_exc.detail["fail_code"] == "T"
