"""Async credit-agency client.

Replacement for the synchronous ``CRDTAGY1..5.cbl`` stub.  Each agency is
modelled as one coroutine on :class:`CreditAgencyClient` that returns an
integer score in ``[0, 999]``; the calling code in
:func:`app.services.support_service.credit_score_check_async` fans out
across all five with :func:`asyncio.gather` and applies a 3-second
timeout, mirroring the ``EXEC CICS DELAY FOR SECONDS(3)`` / FETCH ANY
WAIT EVENT pattern in ``CRECUST.cbl``'s ``CREDIT-CHECK SECTION``.

The COBOL agency programs delay 0-3 seconds and then return a random
score in ``[1, 999]``.  We keep the same semantics and additionally
allow callers to:

* disable the delay (for fast tests),
* seed all randomness via the ``CBSA_CREDIT_AGENCY_SEED`` environment
  variable, for deterministic, reproducible scores.

The client is written against ``httpx.AsyncClient`` so swapping in a
real HTTP backend later is a one-line change.  The actual network call
is gated behind ``mode="stub"`` (default) vs ``mode="http"``.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from collections.abc import Awaitable, Callable
from typing import Literal

import httpx

logger = logging.getLogger("cbsa.credit_agency")

#: Environment variable read at module / client construction time to make
#: random scores and random delays reproducible across runs.
SEED_ENV_VAR = "CBSA_CREDIT_AGENCY_SEED"

#: Lower / upper bound on the credit score returned by an agency.
SCORE_MIN = 0
SCORE_MAX = 999

#: Upper bound on the random ``0..N`` second delay each agency simulates.
DELAY_MAX_SECONDS = 3.0

ClientMode = Literal["stub", "http"]


def _seed_from_env() -> int | None:
    """Return the integer seed configured via ``CBSA_CREDIT_AGENCY_SEED``.

    Returns ``None`` when the environment variable is unset or non-numeric;
    callers then fall back to the system entropy source.
    """
    raw = os.environ.get(SEED_ENV_VAR)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        logger.warning(
            "ignoring non-integer %s=%r; using system entropy instead",
            SEED_ENV_VAR,
            raw,
        )
        return None


class CreditAgencyClient:
    """Async client that fans queries out to 5 mock credit agencies.

    Parameters
    ----------
    mode:
        ``"stub"`` (default) returns scores from a local PRNG; ``"http"``
        issues a GET request against ``base_urls[i]`` for agency ``i``
        and parses ``{"score": int}`` from the JSON response.
    base_urls:
        Per-agency base URLs.  Only consulted when ``mode == "http"``.
        Must contain exactly 5 entries when supplied.
    http_client:
        Optional pre-built :class:`httpx.AsyncClient`; mainly an
        injection point for tests.  When supplied, the caller owns the
        client's lifecycle.
    seed:
        Explicit RNG seed.  ``None`` (the default) falls back to the
        ``CBSA_CREDIT_AGENCY_SEED`` environment variable, then to system
        entropy.
    """

    NUM_AGENCIES = 5

    def __init__(
        self,
        *,
        mode: ClientMode = "stub",
        base_urls: list[str] | None = None,
        http_client: httpx.AsyncClient | None = None,
        seed: int | None = None,
    ) -> None:
        self.mode: ClientMode = mode
        if base_urls is not None and len(base_urls) != self.NUM_AGENCIES:
            raise ValueError(
                f"base_urls must have exactly {self.NUM_AGENCIES} entries; "
                f"got {len(base_urls)}"
            )
        self.base_urls = base_urls
        self._http_client = http_client
        self._owns_http_client = False

        effective_seed = seed if seed is not None else _seed_from_env()
        # Each agency gets its own Random instance derived from the
        # master seed so that two agencies seeded identically don't
        # produce identical scores.  When no seed is set, every agency
        # gets its own unseeded Random (system entropy).
        if effective_seed is None:
            self._rngs = [random.Random() for _ in range(self.NUM_AGENCIES)]
        else:
            self._rngs = [
                random.Random(effective_seed + i) for i in range(self.NUM_AGENCIES)
            ]

    # ------------------------------------------------------------------
    # lifecycle helpers
    # ------------------------------------------------------------------
    async def __aenter__(self) -> "CreditAgencyClient":
        if self.mode == "http" and self._http_client is None:
            self._http_client = httpx.AsyncClient()
            self._owns_http_client = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._owns_http_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
            self._owns_http_client = False

    # ------------------------------------------------------------------
    # public per-agency entrypoints
    # ------------------------------------------------------------------
    async def call_agency_1(self, *, simulate_delay: bool = True) -> int:
        """Mock CRDTAGY1 — see :meth:`_call_agency`."""
        return await self._call_agency(0, simulate_delay=simulate_delay)

    async def call_agency_2(self, *, simulate_delay: bool = True) -> int:
        """Mock CRDTAGY2 — see :meth:`_call_agency`."""
        return await self._call_agency(1, simulate_delay=simulate_delay)

    async def call_agency_3(self, *, simulate_delay: bool = True) -> int:
        """Mock CRDTAGY3 — see :meth:`_call_agency`."""
        return await self._call_agency(2, simulate_delay=simulate_delay)

    async def call_agency_4(self, *, simulate_delay: bool = True) -> int:
        """Mock CRDTAGY4 — see :meth:`_call_agency`."""
        return await self._call_agency(3, simulate_delay=simulate_delay)

    async def call_agency_5(self, *, simulate_delay: bool = True) -> int:
        """Mock CRDTAGY5 — see :meth:`_call_agency`."""
        return await self._call_agency(4, simulate_delay=simulate_delay)

    def agency_callables(
        self, *, simulate_delay: bool = True
    ) -> list[Callable[[], Awaitable[int]]]:
        """Return the 5 agency calls as no-argument coroutine factories.

        Useful for callers that want to fan-out with
        :func:`asyncio.gather` without hardcoding the agency count.
        """
        return [
            lambda: self.call_agency_1(simulate_delay=simulate_delay),
            lambda: self.call_agency_2(simulate_delay=simulate_delay),
            lambda: self.call_agency_3(simulate_delay=simulate_delay),
            lambda: self.call_agency_4(simulate_delay=simulate_delay),
            lambda: self.call_agency_5(simulate_delay=simulate_delay),
        ]

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    async def _call_agency(self, index: int, *, simulate_delay: bool) -> int:
        """Call a single mock agency by 0-based index.

        Matches the CRDTAGY*.cbl behaviour: delay a random 0-3 seconds
        (when requested) and then return an integer score in
        ``[SCORE_MIN, SCORE_MAX]``.  Always reads from the per-agency
        :class:`random.Random` so seeded runs are deterministic.
        """
        rng = self._rngs[index]
        if simulate_delay:
            await asyncio.sleep(rng.uniform(0, DELAY_MAX_SECONDS))

        if self.mode == "http":
            return await self._http_score(index)
        return rng.randint(SCORE_MIN, SCORE_MAX)

    async def _http_score(self, index: int) -> int:
        """Fetch a score via HTTP (``mode == "http"`` only)."""
        if self.base_urls is None:
            raise RuntimeError("CreditAgencyClient(mode='http') requires base_urls")
        url = self.base_urls[index]
        client = self._http_client
        if client is None:
            # Allow callers to use http mode without an `async with`
            # block; we then own the short-lived client.
            async with httpx.AsyncClient() as one_shot:
                response = await one_shot.get(url)
        else:
            response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
        score = int(payload["score"])
        return max(SCORE_MIN, min(SCORE_MAX, score))
