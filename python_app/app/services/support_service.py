"""Supporting services.

Ports of the small COBOL utility programs:

* ``GETSCODE.cbl`` → :func:`get_sort_code`
* ``GETCOMPY.cbl`` → :func:`get_company_name`
* ``CRDTAGY1-5.cbl`` + ``CRECUST.CREDIT-CHECK`` →
  :func:`credit_score_check_async` (async fan-out) and the legacy sync
  shim :func:`credit_score_check`.
* ``ABNDPROC.cbl``  → :func:`abend_handler`
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass

from app.core.config import get_settings
from app.services.credit_agency_client import CreditAgencyClient
from app.services.errors import CreditAgencyTimeoutError

logger = logging.getLogger("cbsa.abend")

#: 3-second window the COBOL ``CRECUST`` parent allows between RUN
#: TRANSID and the first FETCH ANY (``EXEC CICS DELAY FOR SECONDS(3)``).
CREDIT_AGENCY_TIMEOUT_SECONDS = 3.0


def get_sort_code() -> str:
    """Return the bank sort code (see ``GETSCODE.cbl``)."""
    return get_settings().sort_code


def get_company_name() -> str:
    """Return the bank company name (see ``GETCOMPY.cbl``)."""
    return get_settings().company_name


async def credit_score_check_async(
    *,
    simulate_delay: bool = True,
    client: CreditAgencyClient | None = None,
) -> int:
    """Fan-out credit-score check across the 5 mock agencies.

    Ports the ``CREDIT-CHECK SECTION`` of ``CRECUST.cbl``: a RUN TRANSID
    is issued for each of the 5 child agency programs (CRDTAGY1..5),
    the parent waits up to 3 seconds, and the final credit score is the
    average of every agency that replied in time.  If *no* agency
    replied in time the COBOL flow sets ``COMM-FAIL-CODE`` to ``'C'``
    and exits; we mirror that here by raising
    :class:`CreditAgencyTimeoutError`.

    Parameters
    ----------
    simulate_delay:
        When ``True`` (default) each mock agency sleeps for a random
        0–3 seconds before responding, matching the COBOL behaviour.
        Tests typically pass ``False``.
    client:
        Optional pre-built :class:`CreditAgencyClient`.  Most callers
        let the function construct a stub-mode client.
    """
    owns_client = client is None
    if client is None:
        client = CreditAgencyClient()

    try:
        per_agency_calls = [
            asyncio.wait_for(call(), timeout=CREDIT_AGENCY_TIMEOUT_SECONDS)
            for call in client.agency_callables(simulate_delay=simulate_delay)
        ]
        results = await asyncio.gather(*per_agency_calls, return_exceptions=True)
    finally:
        if owns_client:
            await client.__aexit__(None, None, None)

    scores: list[int] = []
    for index, result in enumerate(results, start=1):
        if isinstance(result, asyncio.TimeoutError):
            logger.warning(
                "credit agency %s timed out after %.1fs",
                index,
                CREDIT_AGENCY_TIMEOUT_SECONDS,
            )
        elif isinstance(result, BaseException):
            logger.warning("credit agency %s failed: %s", index, result)
        else:
            scores.append(int(result))

    if not scores:
        raise CreditAgencyTimeoutError(
            "All credit agencies timed out before responding"
        )
    return sum(scores) // len(scores)


def credit_score_check(
    *, simulate_delay: bool = False, rng: random.Random | None = None
) -> int:
    """Synchronous shim around :func:`credit_score_check_async`.

    Preserved so existing callers that cannot easily switch to ``async``
    (and the existing :mod:`tests.test_support_service` cases) keep
    working.  When a deterministic :class:`random.Random` is supplied
    we fall back to the legacy single-RNG path (one score in
    ``[1, 999]``) so the historical contract is preserved; otherwise
    we drive the async fan-out via :func:`asyncio.run` and return the
    averaged score.
    """
    if rng is not None:
        if simulate_delay:
            time.sleep(rng.uniform(0, 3))
        return rng.randint(1, 999)
    return asyncio.run(credit_score_check_async(simulate_delay=simulate_delay))


@dataclass(frozen=True)
class AbendInfo:
    """Replacement for the COBOL ``ABNDINFO`` copybook."""

    program: str
    code: str
    message: str
    sqlcode: int | None = None


def abend_handler(info: AbendInfo) -> None:
    """Record an abend.

    The COBOL ``ABNDPROC.cbl`` writes the abend record to the ``ABNDFILE``
    VSAM file; here we just emit a structured log message.  Centralising
    this keeps the rest of the codebase free of CICS-specific concepts.
    """
    logger.error(
        "abend program=%s code=%s sqlcode=%s: %s",
        info.program,
        info.code,
        info.sqlcode,
        info.message,
    )
