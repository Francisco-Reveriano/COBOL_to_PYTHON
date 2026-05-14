"""FastAPI entrypoint for the CBSA Python port."""

from __future__ import annotations

from fastapi import FastAPI

from app.api import accounts, customers, meta, transfers
from app.insurance.router import router as insurance_router

app = FastAPI(
    title="CBSA Python Port",
    version="0.1.0",
    description=(
        "Python port of the CICS Banking Sample Application (CBSA) and the "
        "GenApp insurance domain.  Business logic was translated from the "
        "COBOL sources in `src/base/cobol_src/` and `cics-genapp/base/src/`; "
        "CICS/DB2/VSAM are replaced with FastAPI, SQLAlchemy, and PostgreSQL."
    ),
)

app.include_router(customers.router)
app.include_router(accounts.router)
app.include_router(transfers.router)
app.include_router(meta.router)
app.include_router(insurance_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
