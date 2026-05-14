# CBSA Python Port

This directory contains a Python port of the **CICS Bank Sample Application (CBSA)**.
It preserves the business rules from the original COBOL programs in `src/base/cobol_src/`
and exposes them via a FastAPI REST service backed by PostgreSQL (SQLAlchemy + Alembic).

## Mapping from COBOL to Python

| COBOL program        | Python module                                  | Purpose                                      |
| -------------------- | ---------------------------------------------- | -------------------------------------------- |
| `CRECUST.cbl`        | `app.services.customer_service.create_customer`| Create customer                              |
| `INQCUST.cbl`        | `app.services.customer_service.get_customer`   | Read customer                                |
| `UPDCUST.cbl`        | `app.services.customer_service.update_customer`| Update customer                              |
| `DELCUS.cbl`         | `app.services.customer_service.delete_customer`| Delete customer (and cascade accounts)       |
| `CREACC.cbl`         | `app.services.account_service.create_account`  | Create account (uses CONTROL row lock + 10-account limit) |
| `INQACC.cbl`         | `app.services.account_service.get_account`     | Read account                                 |
| `INQACCCU.cbl`       | `app.services.account_service.get_accounts_for_customer` | List accounts for a customer       |
| `UPDACC.cbl`         | `app.services.account_service.update_account`  | Update account (type, rate, overdraft, statement dates) |
| `DELACC.cbl`         | `app.services.account_service.delete_account`  | Delete account + write PROCTRAN ODA          |
| `DBCRFUN.cbl`        | `app.services.transaction_service.debit_credit`| Debit/credit + PROCTRAN (PDR/PCR or DEB/CRE) |
| `XFRFUN.cbl`         | `app.services.transaction_service.transfer_funds` | Atomic transfer with lower-account-first lock order |
| `GETSCODE.cbl`       | `app.services.support_service.get_sort_code`   | Return the fixed sort code                   |
| `GETCOMPY.cbl`       | `app.services.support_service.get_company_name`| Return the company name                      |
| `CRDTAGY1-5.cbl`     | `app.services.support_service.credit_score_check` | Stub agency: random delay, random score   |
| `ABNDPROC.cbl`       | `app.services.support_service.abend_handler`   | Python exception/logger replacement          |
| `BANKDATA.cbl`       | `app.db.seed.seed_bank_data`                   | Populate initial test customers and accounts |

## Database schema

The schema is migrated from the COBOL Db2/VSAM copybooks:

- `account` — from `ACCDB2.cpy` / `ACCOUNT.cpy`
- `control` — from `CONTDB2.cpy` / `CONTROLI.cpy`
- `proctran` — from `PROCDB2.cpy` / `PROCTRAN.cpy`
- `customer` — from `CUSTOMER.cpy` (migrated from VSAM to PostgreSQL)

All monetary fields use SQL `NUMERIC` and Python `decimal.Decimal` to match COBOL's
`PIC S9(10)V99 COMP-3` fixed-point arithmetic (never `float`).

## REST API

| Method  | Path                                | COBOL transaction |
| ------- | ----------------------------------- | ----------------- |
| POST    | `/customers`                        | OCCS              |
| GET     | `/customers/{number}`               | ODCS              |
| PUT     | `/customers/{number}`               | UPDCUST           |
| DELETE  | `/customers/{number}`               | DELCUS            |
| GET     | `/customers/{number}/accounts`      | OCCA              |
| POST    | `/accounts`                         | OCAC              |
| GET     | `/accounts/{number}`                | ODAC              |
| PUT     | `/accounts/{number}`                | OUAC              |
| DELETE  | `/accounts/{number}`                | DELACC            |
| POST    | `/accounts/{number}/transactions`   | OCRA              |
| POST    | `/transfers`                        | OTFN              |
| GET     | `/meta/sortcode`                    | GETSCODE          |
| GET     | `/meta/company`                     | GETCOMPY          |

## Running locally

```bash
cd python_app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Point at any PostgreSQL instance — falls back to SQLite at sqlite:///./cbsa.db
export CBSA_DATABASE_URL="postgresql+psycopg2://cbsa:cbsa@localhost:5432/cbsa"

alembic upgrade head
python -m app.db.seed       # optional, seeds test data
uvicorn app.main:app --reload
```

OpenAPI docs are at `http://localhost:8000/docs`.

## Running tests

```bash
cd python_app
pytest -q
```

Tests use a per-test in-memory SQLite database so no PostgreSQL is required to run them.

## Business rules preserved

- **10-account cap per customer** (`CREACC.cbl:347`) — enforced in `create_account`.
- **MORTGAGE/LOAN payment block** (`DBCRFUN.cbl:330`) — enforced in `debit_credit`.
- **Same-account transfer block** (`XFRFUN.cbl:316`) — enforced in `transfer_funds`.
- **Non-positive transfer amount rejected** (`XFRFUN.cbl:289`) — enforced in `transfer_funds`.
- **Insufficient funds check on debits** (`DBCRFUN.cbl:344`) — enforced in `debit_credit`.
- **Lock-order on transfers** — `SELECT … FOR UPDATE` always acquires the lower account
  number first, matching the COBOL's explicit ordering (`XFRFUN.cbl:380`).
- **CONTROL row lock** — `SELECT CONTROL_VALUE_NUM … FOR UPDATE` is used to atomically
  allocate the next account number (replaces CICS ENQ/DEQ on the named counter).
