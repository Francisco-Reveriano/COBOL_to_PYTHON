"""Meta endpoints — sort code and company name (was ``GETSCODE``/``GETCOMPY``)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import CompanyOut, SortCodeOut
from app.services.support_service import get_company_name, get_sort_code

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/sortcode", response_model=SortCodeOut)
def sortcode_endpoint() -> SortCodeOut:
    return SortCodeOut(sort_code=get_sort_code())


@router.get("/company", response_model=CompanyOut)
def company_endpoint() -> CompanyOut:
    return CompanyOut(company_name=get_company_name())
