"""Supporting services.

Ports of the small COBOL utility programs:

* ``GETSCODE.cbl`` → :func:`get_sort_code`
* ``GETCOMPY.cbl`` → :func:`get_company_name`
* ``CRDTAGY1-5.cbl`` → :func:`credit_score_check`
* ``ABNDPROC.cbl``  → :func:`abend_handler`
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass

from app.core.config import get_settings

logger = logging.getLogger("cbsa.abend")


def get_sort_code() -> str:
    """Return the bank sort code (see ``GETSCODE.cbl``)."""
    return get_settings().sort_code


def get_company_name() -> str:
    """Return the bank company name (see ``GETCOMPY.cbl``)."""
    return get_settings().company_name


def credit_score_check(
    *, simulate_delay: bool = True, rng: random.Random | None = None
) -> int:
    """Return a random credit score between 1 and 999.

    The COBOL agency programs (``CRDTAGY1.cbl`` … ``CRDTAGY5.cbl``) delay for
    a random number of seconds (0 – 3) and then return a random score in
    ``[1, 999]``.  We keep the same semantics but allow callers to disable
    the delay (used by tests) and inject a deterministic RNG.
    """
    rng = rng or random.Random()
    if simulate_delay:
        time.sleep(rng.uniform(0, 3))
    return rng.randint(1, 999)


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
