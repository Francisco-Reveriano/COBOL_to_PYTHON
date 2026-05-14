# COBOL → Python Migration — Requirements Document

> **Status:** Draft v0.1 — for stakeholder review
> **Scope:** Re-implementation of the CICS Bank Sample Application (CBSA) and the
> General Insurance Application (GenApp) currently hosted in this repository as a
> cohesive Python service estate that preserves observable business behaviour
> while replacing the COBOL / CICS / VSAM / Db2 runtime.
> **Repository:** `Francisco-Reveriano/COBOL_to_PYTHON`
> **Last updated:** 2026-05-14

---

## 1. Project Scope

### 1.1 In scope

The migration covers **every COBOL program** currently shipped under:

- `src/base/cobol_src/` — CBSA (banking, BMS/Web/REST channels).
- `cics-genapp/base/src/` — GenApp (insurance, BMS channel + SOA shim).

For each program the Python re-implementation must preserve:

- The business outcome (record created, row updated, transaction logged).
- The observable side-effects on the canonical datastore (see §4).
- The externally observable wire contract for any program reachable from BMS,
  the Carbon React UI, or the z/OS Connect / Spring Boot REST surfaces under
  `src/zosconnect_artefacts/` and `src/Z-OS-Connect-*-Interface/`.

### 1.2 Out of scope (initial release)

- Migration of mainframe operational tooling (JCL, RACF, MQ bridges, CICS
  region operator transactions).
- Live cut-over of production data; the v1 release ships a deterministic seed
  generator equivalent to `BANKDATA` only.
- Re-platforming of the Carbon React front-end (`src/bank-application-frontend/`).
  It must continue to work unchanged against the new Python surface.
- The legacy 3270/BMS green-screen interface; equivalent business functions
  will be exposed through the existing REST surfaces only.
- Performance optimisation beyond the targets in §3 (NFR-01).

### 1.3 CBSA programs in scope

| Program     | Type           | Purpose                                                                                                                            | Datastore touched              |
| ----------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| `BNKMENU`   | BMS UI         | Top-level menu; validates option and dispatches to the relevant transaction.                                                       | none                           |
| `BNK1CAC`   | BMS UI         | Create-Account screen; validates input then `LINK`s to `CREACC`.                                                                   | none (delegates)               |
| `BNK1CCA`   | BMS UI         | Lists all accounts for a given customer (calls `INQACCCU`).                                                                        | none (delegates)               |
| `BNK1CCS`   | BMS UI         | Create-Customer screen; validates input then `LINK`s to `CRECUST`.                                                                 | none (delegates)               |
| `BNK1CRA`   | BMS UI         | Credit / Debit screen; validates input then `LINK`s to `DBCRFUN`.                                                                  | none (delegates)               |
| `BNK1DAC`   | BMS UI         | Display-Account screen; also handles account deletion (`LINK`s to `INQACC` / `DELACC`).                                            | none (delegates)               |
| `BNK1DCS`   | BMS UI         | Display-Customer screen; supports update (PF10 → `UPDCUST`) and delete (PF5 → `DELCUS`).                                           | none (delegates)               |
| `BNK1TFN`   | BMS UI         | Funds-Transfer screen between two in-bank accounts (`LINK`s to `XFRFUN`).                                                          | none (delegates)               |
| `BNK1UAC`   | BMS UI         | Update-Account screen (`LINK`s to `UPDACC`).                                                                                       | none (delegates)               |
| `CRECUST`   | Business logic | Enqueue customer counter, run credit checks against `CRDTAGY1..5`, average score, write CUSTOMER + PROCTRAN.                       | CUSTOMER (VSAM), PROCTRAN (DB2) |
| `INQCUST`   | Business logic | Customer enquiry by customer number; returns CUSTOMER record (or low-values if not found).                                         | CUSTOMER (VSAM)                |
| `UPDCUST`   | Business logic | Update permitted customer fields (name, address, credit-score, review date).                                                       | CUSTOMER (VSAM)                |
| `DELCUS`    | Business logic | Cascade-delete all accounts for a customer (PROCTRAN row per deletion) then delete the customer.                                   | CUSTOMER, ACCOUNT, PROCTRAN    |
| `CREACC`    | Business logic | Enqueue account counter, allocate next account number, insert ACCOUNT row, write PROCTRAN.                                         | ACCOUNT (DB2), PROCTRAN (DB2)  |
| `INQACC`    | Business logic | Account enquiry by account number; returns ACCOUNT row.                                                                            | ACCOUNT (DB2)                  |
| `INQACCCU`  | Business logic | List accounts for a given customer number.                                                                                         | ACCOUNT (DB2)                  |
| `UPDACC`    | Business logic | Update permitted account fields (excluding balances).                                                                              | ACCOUNT (DB2)                  |
| `DELACC`    | Business logic | Delete an account row keyed on customer + account_type.                                                                            | ACCOUNT (DB2), PROCTRAN (DB2)  |
| `DBCRFUN`   | Transaction    | Apply a credit or debit to a single account; update `ACCOUNT-ACTUAL-BALANCE` / `ACCOUNT-AVAILABLE-BALANCE`; write PROCTRAN.        | ACCOUNT, PROCTRAN              |
| `XFRFUN`    | Transaction    | Atomic transfer between two in-bank accounts; two PROCTRAN rows; uses syncpoint for consistency.                                   | ACCOUNT (×2), PROCTRAN (×2)    |
| `GETCOMPY`  | Reference      | Return the configured company name.                                                                                                | none                           |
| `GETSCODE`  | Reference      | Return the configured sort code (single sort code per deployment).                                                                 | none                           |
| `CRDTAGY1`  | Credit agency  | Mock agency #1: random 0–3 s delay, random 1–999 score, returned via CICS Async API channel/container.                             | none                           |
| `CRDTAGY2`  | Credit agency  | Mock agency #2 (same contract as `CRDTAGY1`).                                                                                      | none                           |
| `CRDTAGY3`  | Credit agency  | Mock agency #3 (same contract as `CRDTAGY1`).                                                                                      | none                           |
| `CRDTAGY4`  | Credit agency  | Mock agency #4 (same contract as `CRDTAGY1`).                                                                                      | none                           |
| `CRDTAGY5`  | Credit agency  | Mock agency #5 (same contract as `CRDTAGY1`).                                                                                      | none                           |
| `ABNDPROC`  | Error handling | Persist an abend record (`ABNDFILE` KSDS) so that exceptions across the application are observable from one place.                 | ABNDFILE (VSAM)                |
| `BANKDATA`  | Batch          | Seed/initialise CUSTOMER (VSAM) and ACCOUNT (DB2) from a numeric key range supplied as a job parameter.                            | CUSTOMER, ACCOUNT              |

### 1.4 GenApp programs in scope

| Program      | Type           | Purpose                                                                                       | Datastore touched               |
| ------------ | -------------- | --------------------------------------------------------------------------------------------- | ------------------------------- |
| `LGTESTC1`   | BMS UI         | Customer menu — dispatch to add / inquire / update customer.                                  | none                            |
| `LGTESTP1`   | BMS UI         | Motor-policy menu.                                                                            | none                            |
| `LGTESTP2`   | BMS UI         | Endowment-policy menu.                                                                        | none                            |
| `LGTESTP3`   | BMS UI         | House-policy menu.                                                                            | none                            |
| `LGTESTP4`   | BMS UI         | Commercial-policy menu.                                                                       | none                            |
| `LGACUS01`   | Business logic | Add Customer — business orchestration; calls `LGACDB01` (+ `LGACDB02`) or `LGACVS01`.         | CUSTOMER (DB2 / VSAM)           |
| `LGACDB01`   | Data adapter   | Add Customer (DB2): name / address / DOB into customer table.                                 | CUSTOMER (DB2)                  |
| `LGACDB02`   | Data adapter   | Add Customer password row (MD5-checksum default).                                             | SECURITY (DB2)                  |
| `LGACVS01`   | Data adapter   | Add Customer (VSAM KSDS) — VSAM mirror of `LGACDB01`.                                         | CUSTOMER (VSAM)                 |
| `LGICUS01`   | Business logic | Inquire Customer — business orchestration; calls `LGICDB01` or `LGICVS01`.                    | CUSTOMER                        |
| `LGICDB01`   | Data adapter   | Select customer details from DB2.                                                             | CUSTOMER (DB2)                  |
| `LGICVS01`   | Data adapter   | Random customer number from the VSAM KSDS Customer dataset.                                   | CUSTOMER (VSAM)                 |
| `LGUCUS01`   | Business logic | Update Customer — business orchestration; calls `LGUCDB01` or `LGUCVS01`.                     | CUSTOMER                        |
| `LGUCDB01`   | Data adapter   | Update customer details in DB2.                                                               | CUSTOMER (DB2)                  |
| `LGUCVS01`   | Data adapter   | Update customer details in the VSAM KSDS.                                                     | CUSTOMER (VSAM)                 |
| `LGAPOL01`   | Business logic | Add Policy — orchestrate; calls `LGAPDB01` or `LGAPVS01`.                                     | POLICY                          |
| `LGAPDB01`   | Data adapter   | Add full details of a policy to DB2 (Endowment / House / Motor / Commercial).                 | POLICY + sub-tables (DB2)       |
| `LGAPVS01`   | Data adapter   | Add a policy record to the VSAM KSDS Policy file.                                             | POLICY (VSAM)                   |
| `LGIPOL01`   | Business logic | Inquire Policy — orchestrate; calls `LGIPDB01` or `LGIPVS01`.                                 | POLICY                          |
| `LGIPDB01`   | Data adapter   | Read full policy details from DB2.                                                            | POLICY + sub-tables (DB2)       |
| `LGIPVS01`   | Data adapter   | Read / sample a policy record from the VSAM KSDS Policy file.                                 | POLICY (VSAM)                   |
| `LGUPOL01`   | Business logic | Update Policy — orchestrate; calls `LGUPDB01` or `LGUPVS01`.                                  | POLICY                          |
| `LGUPDB01`   | Data adapter   | Update policy details in DB2.                                                                 | POLICY + sub-tables (DB2)       |
| `LGUPVS01`   | Data adapter   | Update policy details in the VSAM KSDS Policy file.                                           | POLICY (VSAM)                   |
| `LGDPOL01`   | Business logic | Delete Policy — orchestrate; calls `LGDPDB01` or `LGDPVS01`.                                  | POLICY                          |
| `LGDPDB01`   | Data adapter   | Delete the policy row from DB2 (and its Endowment / House / Motor / Commercial sub-row).      | POLICY + sub-tables (DB2)       |
| `LGDPVS01`   | Data adapter   | Delete the policy record from the VSAM KSDS Policy file.                                      | POLICY (VSAM)                   |
| `LGWEBST5`   | Web shim       | SOA / web service entry point used by external callers to drive GenApp transactions.          | varies                          |
| `LGSETUP`    | Utility        | Reset the GENACNTL TSQ and recreate the `GENACUSTNUM` named counter after a restore.          | TSQ, named counter              |
| `LGSTSQ`    | Utility        | Write to the GenApp error queue (`GENAERRS` by default; `GENAnnnn` if a `Q=nnnn` parm given). | TSQ                             |
| `LGASTAT1`  | Utility        | Emit run-time / debug information for the current invocation.                                 | none (log only)                 |

---

## 2. Functional Requirements

| ID     | Title                                       | Description                                                                                                                                                                                                                                                                                                                                                          |
| ------ | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-01  | CBSA Customer lifecycle                     | The Python service MUST support create, enquire, update, and cascade-delete of a CBSA customer with the same input validation rules, the same downstream credit-score orchestration (FR-04), and the same PROCTRAN side-effects (`ICC`/`OCC` on create, `IDC`/`ODC` on delete) as `CRECUST`, `INQCUST`, `UPDCUST`, and `DELCUS`.                                       |
| FR-02  | CBSA Account lifecycle                      | The Python service MUST support create, enquire-by-account, list-by-customer, update, and delete of CBSA accounts with the same allocation semantics (named counter for next account number), the same PROCTRAN side-effects (`ICA`/`OCA` on create, `IDA`/`ODA` on delete), and the same per-customer-account-type uniqueness rule enforced by `CREACC` and `DELACC`. |
| FR-03  | CBSA Money movement                         | The Python service MUST support single-account credit / debit (`DBCRFUN`-equivalent) and two-account in-bank transfers (`XFRFUN`-equivalent). Both flows MUST update `ACCOUNT-ACTUAL-BALANCE` and `ACCOUNT-AVAILABLE-BALANCE`, write the corresponding PROCTRAN rows (`CRE`/`DEB`, `TFR`×2, `PCR`/`PDR`), and be atomic — either both legs of a transfer succeed or neither.        |
| FR-04  | Credit-score orchestration                  | Create-customer MUST call five mock credit agencies (parity with `CRDTAGY1..5`) concurrently, wait for all five to complete, average the integer scores into `CUSTOMER-CREDIT-SCORE`, and stamp `CUSTOMER-CS-REVIEW-DATE` 21 days in the future. Each agency MUST preserve the 0–3 s random delay and 1–999 random score behaviour, with a deterministic seed in test mode. |
| FR-05  | Reference data and seeding                  | The service MUST expose `GETCOMPY` / `GETSCODE` equivalents returning the configured company name and sort code, and MUST provide a `BANKDATA`-equivalent seed utility that bulk-populates CUSTOMER and ACCOUNT from a `[from,to,sortcode,seed]` parameter set so existing test corpora continue to work.                                                              |
| FR-06  | GenApp Customer & Policy lifecycle          | The Python service MUST support add / inquire / update of GenApp customers and add / inquire / update / delete of GenApp policies across the four policy types (Endowment, House, Motor, Commercial), preserving the dual-datastore pattern (DB2 + VSAM mirror) at the API contract level even where the physical store changes (see Q-3.1 in §5).                    |
| FR-07  | Error capture and operational observability | All unhandled exceptions and abends raised by any of the in-scope programs MUST be captured in an `ABNDFILE`-equivalent log with the same columns as `ABNDINFO.cpy` (APPLID, TRANID, date, time, code, program, RESP/RESP2/SQLCODE, free-form). The record MUST also be emitted as a structured log event so that downstream observability tooling can consume it.    |

---

## 3. Non-Functional Requirements

| ID      | Category         | Requirement                                                                                                                                                                                                          |
| ------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| NFR-01  | Performance      | Single-account reads (`INQACC`, `INQCUST`) MUST achieve P50 ≤ 50 ms and P95 ≤ 250 ms on a developer laptop with a warm cache. The transfer endpoint (`XFRFUN`) MUST sustain ≥ 100 successful transfers/second per pod. |
| NFR-02  | Correctness      | Monetary values MUST be represented as `decimal.Decimal` in Python and `NUMERIC(14,2)` in the database. Float arithmetic MUST NOT be used at any point in money-handling code paths.                                  |
| NFR-03  | Reliability      | Every business operation that touches more than one row (transfer, cascade delete, create-customer-with-credit-scores) MUST be transactional. Partial writes MUST roll back and emit an FR-07 error record.            |
| NFR-04  | Concurrency      | Counter allocation (`NEWCUSNO`, `NEWACCNO` named-counter equivalents) MUST be safe under concurrent calls. The implementation MUST guarantee no duplicate customer or account numbers across all replicas.            |
| NFR-05  | Security         | All external-facing endpoints MUST support OIDC (Authorization Code + PKCE for UI callers, Client Credentials for service callers), validated via JWKS. Auth MUST be opt-in via a feature flag to preserve drop-in compatibility for existing callers during cut-over. |
| NFR-06  | Compatibility    | The legacy REST shapes documented in `etc/usage/springBoot/doc/CBSA_Restful_API_guide.md` and the swagger artefacts under `src/zosconnect_artefacts/apis/*/api-docs/swagger.json` MUST remain byte-compatible (paths, methods, JSON field names, date formats, sort-code rules) for v1. |
| NFR-07  | Observability    | The service MUST emit OpenTelemetry traces and structured JSON logs for every business operation, with trace ID propagation across credit-agency calls and across the two legs of a transfer.                          |
| NFR-08  | Testability      | A pytest test corpus MUST cover every FR with at least one positive and one negative case. Mock credit agencies MUST accept a deterministic seed so test runs are reproducible. The seed utility MUST support a fixed-seed mode for golden-master tests. |
| NFR-09  | Build & packaging | The Python service MUST build into a single OCI image runnable on Linux/amd64, with deterministic dependency pinning (uv lockfile or equivalent). The existing Java / Maven build (`./mvnw`) MUST remain green during the migration so the parallel-run reference stays usable. |
| NFR-10  | Documentation    | Every public function and endpoint MUST carry an OpenAPI description that includes a back-reference to the originating COBOL program (e.g. `Replaces: CRECUST`). A traceability table MUST be maintained that maps each program in §1.3 / §1.4 to its Python module and to the FR it satisfies. |

---

## 4. Data Model Summary

The migration retains the canonical entities the COBOL code already operates
on. Where a single entity has both VSAM and DB2 representations today, the
Python target collapses to a single relational table; the legacy wire shapes
remain unchanged so callers do not see the change.

### 4.1 CBSA core entities

| Entity      | Today (COBOL)              | Target (Python)                | Key fields (source-of-truth)                                                                                                                  |
| ----------- | -------------------------- | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `CUSTOMER`  | VSAM KSDS (`CUSTOMER.cpy`) | Relational table `customer`    | `sortcode` (9(6)), `customer_number` (9(10)), `name` (60), `address` (160), `dob` (DDMMYYYY), `credit_score` (999), `cs_review_date` (DDMMYYYY) |
| `ACCOUNT`   | DB2 (`ACCOUNT.cpy`)        | Relational table `account`     | `customer_number` (9(10)), `sortcode` (9(6)), `account_number` (9(8)), `type` (X(8)), `interest_rate` (9(4)V99), `actual_balance`, `available_balance` (S9(10)V99) |
| `PROCTRAN`  | DB2 (`PROCTRAN.cpy`)       | Append-only table `proctran`   | `sortcode`, `account_number`, `date` (YYYYMMDD), `time` (HHMMSS), `ref` (9(12)), `type` (3 char — `CRE`/`DEB`/`TFR`/`PCR`/`PDR`/`CHA`/`CHF`/`CHI`/`CHO`/`ICA`/`OCA`/`IDA`/`ODA`/`ICC`/`OCC`/`IDC`/`ODC`/`OCS`), `description` (40), `amount` |
| `CONTROL`   | DB2 (`CONTDB2.cpy`)        | Relational table `control` + named-counter abstraction (`NEWACCNO`, `NEWCUSNO`) | Counter name, current value, last-update timestamp                                                                                            |
| `ABNDFILE`  | VSAM (`ABNDINFO.cpy`)      | Relational table `abnd_file`   | `utime_key` (S9(15)), `taskno` (9(4)), `applid` (X(8)), `tranid` (X(4)), `date` (X(10)), `time` (X(8)), `code` (X(4)), `program` (X(8)), `respcode`, `resp2code`, `sqlcode`, `freeform` (X(600)) |

### 4.2 GenApp core entities

| Entity       | Today (COBOL)            | Target (Python)              | Notes                                                                                                |
| ------------ | ------------------------ | ---------------------------- | ---------------------------------------------------------------------------------------------------- |
| `CUSTOMER`   | DB2 + VSAM (`lgpolicy.cpy` §`DB2-CUSTOMER`) | Relational table `genapp_customer` | `firstname` (10), `lastname` (20), `dateofbirth` (10), `housename` (20), `housenumber` (4), `postcode` (8), `phone_mobile` (20), `phone_home` (20), `email` (100) |
| `POLICY` (header)            | DB2 + VSAM (`lgpolicy.cpy` §`DB2-POLICY`)   | Relational table `genapp_policy`   | `policytype` (X), `policynumber` (9(10)), `issuedate`, `expirydate`, `lastchanged`, `brokerid`, `brokersref`, `payment` |
| `ENDOWMENT`  | DB2 (`DB2-ENDOWMENT`)    | `genapp_endowment` (1:1 with policy) | with-profits, equities, managed-fund flags + fund name + term + sum-assured + life-assured           |
| `HOUSE`      | DB2 (`DB2-HOUSE`)        | `genapp_house`               | property type, bedrooms, value, house name/number, postcode                                          |
| `MOTOR`      | DB2 (`DB2-MOTOR`)        | `genapp_motor`               | make, model, value, reg number, colour, cc, manufactured date, premium, accidents                    |
| `COMMERCIAL` | DB2 (`DB2-COMMERCIAL`)   | `genapp_commercial`          | address, geo (lat/long), customer name, prop type, perils + premiums (fire/crime/flood/weather), status, reject reason |
| `CLAIM`      | DB2 (claim subset)       | `genapp_claim`               | preserved for parity with `WS-CLAIM-LEN`; columns to be enumerated at FR-06 elaboration time         |
| `SECURITY`   | DB2 (`LGACDB02`)         | `genapp_security`            | customer id, password hash (MD5 today — see Q-2.4)                                                   |

### 4.3 Cross-cutting

- Two collapsed datastores (CBSA VSAM `CUSTOMER` and GenApp VSAM mirror) are
  replaced by their relational equivalents. Reads from the legacy "random
  customer" path (`LGICVS01`) become indexed range reads with the same
  randomised result.
- Named counters (`NEWCUSNO`, `NEWACCNO`, `GENACUSTNUM`) become row-locked
  sequences on the `control` table to preserve NFR-04 under concurrency.
- All monetary columns become `NUMERIC(14,2)`; all date columns retain their
  legacy DDMMYYYY / YYYYMMDD wire format on the existing endpoints (see Q-1.2)
  and ISO 8601 on any new endpoint.

---

## 5. Questions for User / Designer

### 5.1 Scope and product

1. **Q-1.1** Are *both* applications (CBSA *and* GenApp) genuinely in scope for
   the first Python release, or do we sequence them (e.g. CBSA → GenApp)?
2. **Q-1.2** Do we need to preserve the legacy date encodings (`DDMMYYYY`
   integers for CBSA, `YYYY-MM-DD` strings for GenApp) on the new endpoints, or
   are we free to use ISO 8601 everywhere?
3. **Q-1.3** Is the Carbon React UI in `src/bank-application-frontend/` the
   only first-party consumer we have to keep working, or are there external
   callers we need to discover and inventory before sign-off?

### 5.2 Data and persistence

4. **Q-2.1** What is the target relational store — PostgreSQL, MySQL, IBM Db2
   on Linux, or other? This decision affects locking semantics for NFR-04 and
   the choice of `NUMERIC` precision in §4.
5. **Q-2.2** For GenApp, do the *current* deployments rely on the VSAM mirror
   being readable independently of DB2 (e.g. a separate batch reads VSAM
   directly), or is the dual-store pattern purely historical?
6. **Q-2.3** Is a one-shot live-data migration required (e.g. Db2 unload →
   CSV → `COPY`), or is generative seeding (`BANKDATA`-equivalent) sufficient
   for v1?
7. **Q-2.4** The GenApp `SECURITY` table currently stores an MD5 default
   password. Should the Python re-implementation upgrade to a modern KDF
   (Argon2id / bcrypt) on first use, and what is the rollover plan for existing
   hashes?

### 5.3 Functional behaviour

8. **Q-3.1** Should the five CBSA credit agencies (`CRDTAGY1..5`) remain *five
   distinct mock services* so the parallel-fan-out shape stays observable for
   teaching, or should we consolidate them behind a single mock with five
   logical agency IDs?
9. **Q-3.2** Are the `PROC-TRAN-TYPE` codes (`CRE`, `DEB`, `TFR`, `PCR`, `PDR`,
   `CHA`, `CHF`, `CHI`, `CHO`, `ICA`, `OCA`, `IDA`, `ODA`, `ICC`, `OCC`, `IDC`,
   `ODC`, `OCS`) all in scope, or are some (e.g. the cheque-handling codes
   `CHA`/`CHF`/`CHI`/`CHO`) safe to omit because there is no calling program in
   this repository?
10. **Q-3.3** GenApp policies span four product types (Endowment, House, Motor,
    Commercial). Do we ship all four in v1, or do we pick one as a vertical
    slice (most likely Motor or House) and follow up with the rest?

### 5.4 Non-functional and operational

11. **Q-4.1** Are the performance targets in NFR-01 (P50 ≤ 50 ms, P95 ≤ 250 ms,
    ≥ 100 transfers/sec) the right SLOs, or are there contractual / regulatory
    targets we should align to instead?
12. **Q-4.2** Is OIDC / OAuth 2.0 (NFR-05) the right auth target, or do we
    need to integrate with an existing enterprise IdP (e.g. SAML federation,
    mTLS for service-to-service)?
13. **Q-4.3** Do we need to keep the legacy COBOL build / runtime in this
    repository green during the migration as a parallel-run reference, or can
    we delete it once the Python service ships?

---

## 6. Assumptions

- **A-01** The Python target runs on a modern Linux container platform
  (Kubernetes or equivalent). On-prem mainframe co-location is out of scope.
- **A-02** A single relational database is the system of record. VSAM-only
  reads are emulated against the same table the DB2 path now writes to.
- **A-03** The deployment is single-tenant (one bank / one insurer); the
  `sortcode` field is taken from configuration (`CBSA_SORTCODE`, default
  `987654`) rather than a request-scoped header.
- **A-04** Wire formats documented in `etc/usage/springBoot/doc/CBSA_Restful_API_guide.md`
  and in `src/zosconnect_artefacts/apis/*/api-docs/swagger.json` are
  authoritative. Where the COBOL and the swagger disagree, swagger wins.
- **A-05** The Carbon React UI in `src/bank-application-frontend/` is the
  only first-party UI consumer in scope, and is treated as a black-box.
- **A-06** The mock credit agencies remain probabilistic in production but
  honour a deterministic seed in test mode (NFR-08).
- **A-07** The legacy COBOL build (`pom.xml`, `mvnw`, JCL under
  `etc/install/base/`) is preserved for parallel-run reference and is not
  modified by this migration.
- **A-08** Monetary fields are `decimal.Decimal` end-to-end (NFR-02). JSON
  serialisation emits monetary values as numbers with up to 2 decimal places.
- **A-09** Idempotency for money-movement endpoints is enforced via an
  `Idempotency-Key` header with a 24-hour replay window scoped per (caller,
  route); duplicate keys return the original response unchanged.
- **A-10** Abend / error capture (FR-07) is structured-log first, with the
  `ABNDFILE`-equivalent table preserved column-for-column so existing
  dump-analysis tooling can keep parsing it.

---

> *This document is intentionally implementation-light. Detailed API contracts,
> request/response schemas, and per-program traceability live in the migration
> design specification produced after the questions in §5 have been answered.*
