"""Customer service — ports the COBOL CUSTOMER programs.

* ``CRECUST.cbl`` → :func:`create_customer`
* ``INQCUST.cbl`` → :func:`get_customer`
* ``UPDCUST.cbl`` → :func:`update_customer`
* ``DELCUS.cbl``  → :func:`delete_customer` (cascades accounts)
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import decimal as _d

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Account, Control, Customer, ProcTran
from app.models.proctran import (
    PROC_TYPE_BRANCH_CREATE_CUSTOMER,
    PROC_TYPE_BRANCH_DELETE_ACCOUNT,
    PROC_TYPE_BRANCH_DELETE_CUSTOMER,
)
from app.services.common import (
    control_name_for_customer_count,
    control_name_for_customer_last,
    fmt_customer_number,
    now,
    sort_code,
    today,
)
from app.services.errors import NotFoundError
from app.services.support_service import credit_score_check_async


def _ensure_control(session: Session, name: str) -> Control:
    """Get-or-create a ``CONTROL`` row using ``SELECT … FOR UPDATE``."""
    stmt = select(Control).where(Control.name == name).with_for_update()
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        row = Control(name=name, value_num=0, value_str="")
        session.add(row)
        session.flush()
    return row


def create_customer(
    session: Session,
    *,
    name: str,
    address: str,
    date_of_birth: _dt.date,
    credit_score: int | None = None,
    cs_review_date: _dt.date | None = None,
) -> Customer:
    """Create a new customer (port of ``CRECUST.cbl``).

    Allocates the next customer number under a row-level lock on the
    ``CONTROL`` table (replacing CICS NCS ENQ/DEQ) and writes a PROCTRAN
    ``OCC`` record.  If no credit score is supplied, the credit-agency
    stub is invoked synchronously.
    """
    sc = sort_code()

    count = _ensure_control(session, control_name_for_customer_count(sc))
    last = _ensure_control(session, control_name_for_customer_last(sc))

    new_number = last.value_num + 1
    last.value_num = new_number
    count.value_num = count.value_num + 1

    if credit_score is None:
        # CRECUST fans out to 5 credit agencies (CRDTAGY1..5) and averages
        # whichever replied within the 3-second WAIT EVENT.  Drive the
        # async fan-out from this sync entrypoint via asyncio.run so the
        # service contract (and existing callers) stays unchanged.
        credit_score = asyncio.run(credit_score_check_async(simulate_delay=False))
    if cs_review_date is None:
        # FR-04 / CRECUST WS-REVIEW-DATE-ADD: stamp the credit-score
        # review date 21 days in the future (CRECUST.cbl:775-780 sets
        # the review date within the next 21 days).  The requirements
        # doc fixes this to a constant 21-day window for determinism;
        # the COBOL randomises within 1..21.
        cs_review_date = today() + _dt.timedelta(days=21)

    customer = Customer(
        eyecatcher="CUST",
        sortcode=sc,
        number=fmt_customer_number(new_number),
        name=name,
        address=address,
        date_of_birth=date_of_birth,
        credit_score=credit_score,
        cs_review_date=cs_review_date,
    )
    session.add(customer)
    session.flush()

    n = now()
    session.add(
        ProcTran(
            eyecatcher="PRTR",
            sortcode=sc,
            number="00000000",
            date=n.date(),
            time=n.time().replace(microsecond=0),
            ref="",
            type=PROC_TYPE_BRANCH_CREATE_CUSTOMER,
            description=f"{customer.number}{name[:14]:<14}",
            amount=_d.Decimal("0.00"),
        )
    )
    session.flush()
    return customer


def get_customer(session: Session, number: int | str) -> Customer:
    """Read a customer (port of ``INQCUST.cbl``)."""
    sc = sort_code()
    stmt = select(Customer).where(
        Customer.sortcode == sc, Customer.number == fmt_customer_number(number)
    )
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"Customer {number} not found")
    return row


def update_customer(
    session: Session,
    number: int | str,
    *,
    name: str | None = None,
    address: str | None = None,
    date_of_birth: _dt.date | None = None,
    credit_score: int | None = None,
    cs_review_date: _dt.date | None = None,
) -> Customer:
    """Update an existing customer (port of ``UPDCUST.cbl``).

    Only the fields supplied are modified; missing values keep their
    existing value (matching ``UPDCUST``'s field-level UPDATE behaviour).
    """
    customer = get_customer(session, number)
    if name is not None:
        customer.name = name
    if address is not None:
        customer.address = address
    if date_of_birth is not None:
        customer.date_of_birth = date_of_birth
    if credit_score is not None:
        customer.credit_score = credit_score
    if cs_review_date is not None:
        customer.cs_review_date = cs_review_date
    session.flush()
    return customer


def delete_customer(session: Session, number: int | str) -> Customer:
    """Delete a customer (port of ``DELCUS.cbl``).

    Mirrors the COBOL behaviour: deletes every account belonging to the
    customer first (writing one PROCTRAN ``ODA`` per account), then deletes
    the customer row and writes a PROCTRAN ``ODC``.
    """
    customer = get_customer(session, number)

    accounts = (
        session.execute(
            select(Account).where(Account.customer_number == customer.number)
        )
        .scalars()
        .all()
    )
    n = now()
    for acc in accounts:
        session.add(
            ProcTran(
                eyecatcher="PRTR",
                sortcode=acc.sortcode,
                number=acc.number,
                date=n.date(),
                time=n.time().replace(microsecond=0),
                ref="",
                type=PROC_TYPE_BRANCH_DELETE_ACCOUNT,
                description=(f"{customer.number}{acc.type:<8}DELETE")[:40],
                amount=acc.actual_balance,
            )
        )
    if accounts:
        session.execute(
            delete(Account).where(Account.customer_number == customer.number)
        )

    session.delete(customer)
    session.add(
        ProcTran(
            eyecatcher="PRTR",
            sortcode=customer.sortcode,
            number="00000000",
            date=n.date(),
            time=n.time().replace(microsecond=0),
            ref="",
            type=PROC_TYPE_BRANCH_DELETE_CUSTOMER,
            description=f"{customer.sortcode}{customer.number}{customer.name[:14]:<14}",
            amount=_d.Decimal("0.00"),
        )
    )

    # Keep the CONTROL counter in sync so the next INQCONT sees the new total.
    sc = sort_code()
    count = _ensure_control(session, control_name_for_customer_count(sc))
    if count.value_num > 0:
        count.value_num -= 1
    session.flush()
    return customer
