# CBSA → Python 3.12 Migration — Initial Project Plan

> SDLC Artifact: **Initial Project Plan (IPP)**
> Status: **Draft v0.2** — for stakeholder review (Python migration scope)
> Owner: Project Management Office (PMO)
> Cadence: 6 months, 3 phases, two-week sprints (13 sprints)
> Last updated: 2026-05-14

---

## 1. Document Control

| Field             | Value                                                                                                                                                              |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Project name      | CBSA + GenApp → Python 3.12 Migration                                                                                                                              |
| Project sponsor   | TBD (Executive Sponsor — Banking & Insurance Modernization)                                                                                                        |
| Project manager   | TBD                                                                                                                                                                |
| Technical lead    | TBD                                                                                                                                                                |
| SDLC stage        | Initiation / Planning                                                                                                                                              |
| Document type     | Initial Project Plan (IPP)                                                                                                                                         |
| Related artifacts | Architecture guide (`doc/CBSA_Architecture_guide.md`), Requirements (`doc/COBOL_to_Python_Requirements.md`), Software Design Document (`doc/Software_Design_Document.md`), existing Python port (`python_app/README.md`) |
| Approval gate     | Phase-gate review at the end of each phase                                                                                                                         |

### Revision History

| Version | Date       | Author | Notes                                                                                                                                                       |
| ------- | ---------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0.1     | 2026-05-14 | PMO    | Initial draft for stakeholder review — covered the legacy COBOL/CICS install rollout (VSAM, Db2, BMS, Liberty JVM server, Spring Boot REST interfaces).      |
| 0.2     | 2026-05-14 | PMO    | **Rewritten for Python 3.12 migration scope.** Aligned to the Requirements document (FR-01…FR-07, NFR-01…NFR-10) and the Software Design Document's recommended Architecture C (Modular Monolith with FastAPI). Acknowledges that CBSA banking Python services are already substantially complete in `python_app/`. |

---

## 2. Executive Summary

This Initial Project Plan governs the migration of the CICS Bank Sample Application (CBSA) and the General Insurance Application (GenApp) from their legacy COBOL / CICS / Db2 / VSAM runtime to **Python 3.12 + FastAPI + PostgreSQL**, over a six-month delivery window organised into three project phases that align to the five technical phases of the Software Design Document (SDD §9). The Carbon React SPA in `src/bank-application-frontend/` is preserved as-is and is only repointed at the new backend via an environment variable.

A first vertical slice of the target architecture is already in the repository under `python_app/` — FastAPI app, SQLAlchemy models for `account`/`control`/`customer`/`proctran`, service layer for the CBSA core (customer, account, transaction, support), an Alembic initial migration, deterministic seed, and a pytest corpus covering the services and the API. The remaining work concentrates on restructuring this slice into the SDD's modular-monolith layout, adding the insurance (GenApp) module, hardening the API contract against the existing z/OS Connect surface, repointing the React UI, and decommissioning the COBOL backend.

1. **Phase 1 — Data Migration + Core Business Logic (Months 1–2, Sprints S1–S4).** Stand up PostgreSQL with `banking.*` and `insurance.*` schemas (SDD §9 Phase 1) and implement the service layer per the COBOL-to-Python mapping table (SDD §7) into `app/banking/` and `app/insurance/`. Banking is largely **carry-over** from the existing `python_app/` services — the work is restructuring to the SDD §8 layout, completing the `abnd_file` table and async credit-agency fan-out (FR-04, FR-07), and adding the full GenApp domain. Phase 1 exits when 100% of FR-01…FR-07 are implemented with ≥90% test coverage (NFR-08) against PostgreSQL (and SQLite in CI).

2. **Phase 2 — API Layer + UI Integration (Months 3–4, Sprints S5–S8).** Publish FastAPI routers under `/api/v1/banking/*` and `/api/v1/insurance/*` whose paths, methods, request shapes, response shapes, and HTTP status semantics match the existing z/OS Connect API definitions in `src/zosconnect_artefacts/` and the Spring Boot REST guide (`etc/usage/springBoot/doc/CBSA_Restful_API_guide.md`) byte-for-byte (NFR-06). Validate the contract with Schemathesis. Repoint the Carbon React SPA at the FastAPI base URL via a single `.env` variable. Run the Python service **side-by-side** with the COBOL backend for two weeks until the response diff is zero (SDD §9 Phase 2 / §10 mitigations).

3. **Phase 3 — Hardening + Decommission (Months 5–6, Sprints S9–S13).** Add OIDC authentication behind a feature flag (NFR-05), OpenTelemetry traces with cross-leg propagation (NFR-07), structured JSON logging, an OCI image with deterministic dependency pinning (NFR-09), and full operational runbooks. Ramp production traffic 1 % → 10 % → 50 % → 100 % over four weeks, freeze writes to the COBOL backend, archive the legacy COBOL/Spring Boot/z/OS Connect surfaces, and complete the project closeout.

The plan is deliberately conservative: it preserves every business behaviour observable through the existing REST contract, leaves the Carbon React UI unchanged, and treats the COBOL backend as a hot rollback target for one quarter after cut-over.

---

## 3. Goals and Objectives

### Business Goals

- Replace the COBOL / CICS / Db2 / VSAM runtime with a single Python 3.12 + FastAPI + PostgreSQL service estate while preserving every observable business behaviour of CBSA and GenApp.
- Reduce ongoing operational cost by eliminating the dependency on a mainframe CICS region, z/OS Connect, the Liberty JVM server, and the two Spring Boot REST gateways (`src/Z-OS-Connect-Customer-Services-Interface/`, `src/Z-OS-Connect-Payment-Interface/`).
- Unlock cloud-native delivery patterns (containerised deploys, horizontal scaling, OpenTelemetry-based observability) for the banking platform.
- Keep the modern Carbon React UI (`src/bank-application-frontend/`) as the user-facing product unchanged — only the backend changes underneath it.

### Technical Objectives

- Adopt **Architecture C — Modular Monolith (FastAPI)** from the SDD (SDD §4.3 and §6) as the target architecture, with package-level enforcement of the `app.banking` / `app.insurance` / `app.shared` boundary via `import-linter`.
- Implement the SDD's COBOL-to-Python mapping table (SDD §7.1, §7.2, §7.3) so every program in `src/base/cobol_src/` and `cics-genapp/base/src/` has a named Python module (or an explicit "replaced by React" entry).
- Use **SQLAlchemy** for ORM, **Alembic** for migrations, **PostgreSQL** as the canonical store (with SQLite in CI), **`asyncio` + `httpx`** for the credit-agency fan-out replacing CICS Async API, and **Pydantic** for all request/response schemas.
- Preserve the legacy REST shapes from `src/zosconnect_artefacts/apis/*/api-docs/swagger.json` and `etc/usage/springBoot/doc/CBSA_Restful_API_guide.md` byte-compatibly (NFR-06).
- Treat the existing `python_app/` as the seed for Phase 1 — its CBSA services, models, Alembic migration, seed, and tests are carry-over work to be restructured (not rewritten) into the SDD §8 layout.

### Success Metrics (KPIs)

| KPI                                                       | Target                                                                                  | Source           |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------- | ---------------- |
| Phase-gate sign-off on schedule                           | 3 / 3 phases                                                                            | This plan        |
| FR coverage at Phase 1 exit (FR-01…FR-07)                 | 100 %                                                                                   | Requirements §2  |
| Pytest line coverage on `app/banking/` and `app/insurance/` | ≥ 90 %                                                                                  | NFR-08           |
| `INQACC` / `INQCUST` read latency (warm cache, laptop)    | P50 ≤ 50 ms, P95 ≤ 250 ms                                                               | NFR-01           |
| `XFRFUN` throughput per pod                               | ≥ 100 successful transfers/sec                                                          | NFR-01           |
| REST contract conformance vs. z/OS Connect swagger        | 100 % of paths / methods / shapes (Schemathesis suite green)                            | NFR-06           |
| Side-by-side COBOL vs. Python response diff (Phase 2 end) | 0 differences over a 2-week replay window                                               | SDD §9 Phase 2   |
| Production traffic served by Python at Phase 3 exit       | 100 % for one full week, SLOs ≥ COBOL baseline                                          | SDD §9 Phase 4   |
| Defect leakage to UAT (Sev 1/2)                           | 0                                                                                       | Phase-gate       |
| Documentation coverage                                    | Every public function and endpoint carries an OpenAPI description with `Replaces: <COBOL>` back-reference | NFR-10 |

---

## 4. Scope

### 4.1 In Scope

- **All 29 CBSA COBOL programs** in `src/base/cobol_src/` (per Requirements §1.3 and SDD §3.2.1) — BMS handlers (`BNK1*`, `BNKMENU`), business logic (`CRECUST`, `INQCUST`, `UPDCUST`, `DELCUS`, `CREACC`, `INQACC`, `INQACCCU`, `UPDACC`, `DELACC`), transactions (`DBCRFUN`, `XFRFUN`), reference (`GETCOMPY`, `GETSCODE`), credit agencies (`CRDTAGY1..5`), error handling (`ABNDPROC`), and the seed batch (`BANKDATA`).
- **All 31 GenApp COBOL programs** in `cics-genapp/base/src/` (per Requirements §1.4 and SDD §3.2.2) — BMS menus (`LGTEST*`), customer flow (`LGACUS01`, `LGACDB01`, `LGACVS01`, `LGICUS01`, `LGUCUS01`), policy flow (`LGAPOL01`, `LGIPOL01`, `LGUPOL01`, `LGDPOL01` and their `DB*`/`VS*` adapters), claim and stats (`LGSTSQ`, `LGASTAT1`), and the four policy sub-types (Endowment, House, Motor, Commercial).
- **Data migration** of the canonical CBSA entities (`CUSTOMER`, `ACCOUNT`, `CONTROL`, `PROCTRAN`, `ABNDFILE`) and GenApp entities (`CUSTOMER`, `POLICY`, `ENDOWMENT`, `HOUSE`, `MOTOR`, `COMMERCIAL`, `CLAIM`, `SECURITY`) from Db2 + VSAM to PostgreSQL relational tables (Requirements §4, SDD §9 Phase 1). Dual-store entities collapse to a single relational table; the legacy wire shapes are preserved (NFR-06).
- **REST contract preservation**: paths, methods, JSON field names, date formats, and sort-code rules from `src/zosconnect_artefacts/apis/*/api-docs/swagger.json` and `etc/usage/springBoot/doc/CBSA_Restful_API_guide.md` remain byte-compatible for v1 (NFR-06).
- **Carry-over of `python_app/`**: the existing CBSA Python port (FastAPI app, SQLAlchemy models, services, Alembic migration, seed, tests) is the starting point for Phase 1. The work is restructuring to the SDD §8 layout, not rewriting.
- **Carbon React UI repoint**: change a single `.env` variable in `src/bank-application-frontend/` to point at the FastAPI base URL. No React source code changes.
- **Hardening**: OIDC authentication (NFR-05), OpenTelemetry + structured JSON logging (NFR-07), OCI image build with deterministic lockfile (NFR-09), full Python documentation and traceability table (NFR-10).
- **Decommission** of the COBOL backend, Spring Boot REST gateways, z/OS Connect artefacts, BMS transactions, and Db2/VSAM allocations after a one-quarter rollback window (SDD §9 Phase 5).

### 4.2 Out of Scope

- **Rewriting the Carbon React UI** in `src/bank-application-frontend/`. It stays as-is — only the backend URL in `.env` changes (Requirements §1.2).
- **Live cut-over of production data for v1.** The first release ships a deterministic seed generator equivalent to `BANKDATA` (Requirements §1.2). One-shot live-data migration is deferred to a follow-on release pending the Q-2.3 decision.
- **The legacy 3270 / BMS green-screen interface.** Equivalent business functions are exposed only through the existing REST surfaces (Requirements §1.2). The `OMEN` transaction and all `BNK1*` BMS handlers are retired in Phase 3.
- **Migration of mainframe operational tooling** — JCL, RACF, MQ bridges, CICS region operator transactions (Requirements §1.2).
- **Performance optimisation beyond the NFR-01 targets** (Requirements §1.2).
- **Re-platforming or material refactoring of the existing Java / Maven build (`./mvnw`).** It must remain green during the migration so the parallel-run reference stays usable (NFR-09).
- **Production hardening of the mainframe** (HA, DR, capacity uplift). The COBOL backend is treated as a quarantined rollback target only.

### 4.3 Assumptions

- A PostgreSQL instance (15 or later) is available for development, staging, and production. Local development uses Docker Compose; CI uses SQLite for fast feedback.
- Python 3.12 is the runtime everywhere; dependencies are pinned via `uv` (or `pip-tools`) and built into a single OCI image (NFR-09).
- The existing z/OS Connect swagger artefacts in `src/zosconnect_artefacts/` are the **authoritative source of truth** for the v1 REST contract (NFR-06).
- The CICS / Db2 backend remains readable throughout Phases 1–3 to support the side-by-side runner.
- The Carbon React UI in `src/bank-application-frontend/` accepts a backend URL via an environment variable and does not require code changes to be repointed.
- Approval on the open Requirements questions (Q-1.1 … Q-3.2) is received in Sprint S1; in their absence, the defaults documented alongside each question in §11 below apply.

### 4.4 Constraints

- The REST contract is frozen at the shape published by the existing z/OS Connect / Spring Boot surfaces (NFR-06). New fields or breaking changes require a v2 surface.
- Monetary values MUST be `decimal.Decimal` in Python and `NUMERIC(14,2)` in PostgreSQL; float arithmetic is prohibited in money-handling paths (NFR-02).
- Two-week sprint cadence is fixed; phase boundaries align with sprint boundaries.
- No changes to the React UI source — only `.env`.

---

## 5. Phased Delivery Timeline

The SDD's five technical phases (SDD §9) collapse into three project phases of approximately two months each. Phase boundaries align with sprint boundaries (13 two-week sprints; Sprint S13 doubles as the closeout sprint).

```
Month:   1     2     3     4     5     6
Sprint:  1  2  3  4  5  6  7  8  9 10 11 12 13
Phase:  [-----Phase 1-----][----Phase 2----][--Phase 3--]
SDD §9: [P1 Data][--P2 Logic--][--P3 API--][P4 UI/Run ][P5 Decom]
```

### 5.1 Phase 1 — Data Migration + Core Business Logic (Months 1–2)

**Phase goal:** Land the SDD §8 directory structure, finish migrating the CBSA banking domain into it, and add the GenApp insurance domain — all driven by Alembic against PostgreSQL with full pytest coverage (NFR-08).

**Starting point:** The existing `python_app/` already contains a FastAPI app, SQLAlchemy models for `account`/`control`/`customer`/`proctran`, services for customer / account / transaction / support, an Alembic initial migration (`alembic/versions/0001_initial_schema.py`), a deterministic seed (`app/db/seed.py`), and a pytest corpus (`test_customer_service.py`, `test_account_service.py`, `test_transaction_service.py`, `test_api.py`, `test_support_service.py`, `test_seed.py`). Phase 1 reorganises this slice into the SDD §8 layout, extends it, and adds the insurance domain — it does not throw it away.

| Sprint | Weeks | Focus                                                | Key Deliverables                                                                                                                                                                                                                                                                                                                                                                          |
| ------ | ----- | ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1     | 1–2   | Mobilisation, environment, package boundary          | Project kickoff and RACI signed; PostgreSQL stood up locally via `docker-compose.yml`; Python 3.12 + `uv` toolchain confirmed; `import-linter` ruleset committed enforcing the SDD §8 boundary (`app.banking` ⊥ `app.insurance`; `shared`/`db` may not import either) (SDD §8); open Requirements questions (Q-1.1 … Q-3.2) resolved.                                                |
| S2     | 3–4   | SDD §8 restructure of banking + abnd_file + counters | `python_app/app/` reorganised into `app/banking/{routers,schemas,models,services,repositories,clients}/`, `app/shared/`, and `app/db/` per SDD §8; existing services for customer / account / transaction / support carried over into `app/banking/services/`; `abnd_file` table added (FR-07, Requirements §4.1); `counters.py` repository wired to `pg_advisory_xact_lock` for `NEWCUSNO` / `NEWACCNO` (NFR-04, SDD §7.3). |
| S3     | 5–6   | Async credit-agency fan-out + GenApp scaffolding     | `app/banking/clients/credit_agency.py` implements parallel calls to five mock agencies via `httpx.AsyncClient` + `asyncio.gather`, wrapped in `asyncio.wait_for(..., timeout=3.0)` to match `CRECUST`'s 3-second CICS Async wait (FR-04, SDD §10); deterministic seed mode for tests (NFR-08); `app/insurance/` package skeleton (routers, schemas, models, services, repositories) created per SDD §8. |
| S4     | 7–8   | GenApp services + Phase 1 gate                       | All 31 GenApp programs from `cics-genapp/base/src/` mapped to `app/insurance/services/` per SDD §7.2 (customer add/inquire/update via `LGACUS01`/`LGICUS01`/`LGUCUS01`, policy lifecycle across the four sub-types via `LGAPOL01`/`LGIPOL01`/`LGUPOL01`/`LGDPOL01`, stats via `LGASTAT1`); Alembic migrations complete for every CBSA + GenApp entity in Requirements §4.1 / §4.2; pytest line coverage ≥ 90 % on `app/banking/` and `app/insurance/` (NFR-08); Phase 1 closeout review and gate approval. |

**Phase 1 exit criteria**

- 100 % of FR-01 … FR-07 (Requirements §2) implemented in `app/banking/` and `app/insurance/`.
- Pytest corpus passes against in-memory SQLite (CI) and against a local PostgreSQL container (developer laptop); coverage ≥ 90 % (NFR-08).
- `import-linter` passes; no `app.banking` ↔ `app.insurance` imports.
- All monetary fields use `decimal.Decimal` / `NUMERIC(14,2)` (NFR-02); float arithmetic absent from money-handling paths.
- Alembic migrations apply cleanly on an empty PostgreSQL from `alembic upgrade head`.
- Deterministic seed scripts (`scripts/seed_banking.py`, `scripts/seed_insurance.py`) populate the canonical entities and are reproducible from a fixed RNG seed (NFR-08).

### 5.2 Phase 2 — API Layer + UI Integration (Months 3–4)

**Phase goal:** Publish a FastAPI surface that is **byte-compatible** with the existing z/OS Connect REST contract (NFR-06), repoint the Carbon React UI at it, and prove parity by running the two backends side-by-side until the response diff is zero (SDD §9 Phase 2 / Phase 3).

| Sprint | Weeks | Focus                                            | Key Deliverables                                                                                                                                                                                                                                                                                                                                  |
| ------ | ----- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S5     | 9–10  | FastAPI router parity with z/OS Connect          | `app/banking/routers.py` and `app/insurance/routers.py` publish endpoints whose paths, methods, request shapes, response shapes, HTTP status semantics, date encodings (DDMMYYYY / YYYYMMDD per Requirements §4.3), and error envelopes match `src/zosconnect_artefacts/apis/*/api-docs/swagger.json` and `etc/usage/springBoot/doc/CBSA_Restful_API_guide.md` (NFR-06). |
| S6     | 11–12 | Schemathesis contract tests                      | Schemathesis suite runs against the generated FastAPI OpenAPI spec and against the legacy swagger, with property-based negative cases; suite added to CI (`tests/e2e/test_react_contract.py` per SDD §8); FastAPI exception handlers populate `abnd_file` and emit structured log events (FR-07, NFR-07).                                              |
| S7     | 13–14 | Side-by-side runner against COBOL backend        | Diff harness replays a recorded production-shape traffic sample against both the Python service and the COBOL z/OS Connect surface; per-request JSON diff is logged; pricing, dates, sort-code, and PROCTRAN row counts are checked; diff log reviewed daily (SDD §9 Phase 2, SDD §10 first risk row).                                              |
| S8     | 15–16 | React `.env` repoint + Phase 2 gate              | Single-line change to `src/bank-application-frontend/.env` to point at the FastAPI base URL; smoke test the full Carbon React UI against Python; two consecutive weeks of zero side-by-side diff captured; Phase 2 closeout review and gate approval.                                                                                              |

**Phase 2 exit criteria**

- Schemathesis suite is green against the full set of z/OS Connect APIs in `src/zosconnect_artefacts/apis/`.
- Side-by-side runner records zero functional differences over a 2-week window (SDD §9 Phase 2).
- Carbon React UI exercises every documented banking and insurance flow against the FastAPI backend with no UI source changes.
- No regression in the Java / Maven build (`./mvnw`) (NFR-09).
- `/healthz` and `/readyz` endpoints are live (SDD §9 Phase 3).

### 5.3 Phase 3 — Hardening + Decommission (Months 5–6)

**Phase goal:** Make the Python service production-grade (NFR-05 / NFR-07 / NFR-09), ramp production traffic onto it, and retire the COBOL / z/OS Connect / Spring Boot surfaces (SDD §9 Phase 4 + Phase 5).

| Sprint | Weeks | Focus                                                | Key Deliverables                                                                                                                                                                                                                                                                                          |
| ------ | ----- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S9     | 17–18 | OIDC auth (feature-flagged) + observability          | OIDC dependency added to `app/shared/auth.py` (Authorization Code + PKCE for UI callers, Client Credentials for service callers, JWKS validation) gated by a feature flag for drop-in compatibility during cut-over (NFR-05); OpenTelemetry tracer + structured JSON logging wired across the credit-agency fan-out and across both legs of `XFRFUN` (NFR-07). |
| S10    | 19–20 | OCI image, deploy pipeline, load test                | Dockerfile + GitHub Actions / pipeline produces a single OCI image for Linux/amd64 with a `uv` lockfile (NFR-09); load test confirms NFR-01 targets (`INQACC`/`INQCUST` P50 ≤ 50 ms / P95 ≤ 250 ms; `XFRFUN` ≥ 100 transfers/sec/pod).                                                                  |
| S11    | 21–22 | Production ramp 1 % → 10 % → 50 %                    | Traffic split via feature flag or weighted DNS; per-percentage soak windows; SLOs monitored against the COBOL baseline (SDD §9 Phase 4); reconciliation diff alerts wired to on-call.                                                                                                                  |
| S12    | 23–24 | 100 % traffic on Python + COBOL freeze               | 100 % of UI and partner-API traffic served by Python for one full week with SLOs ≥ COBOL baseline (SDD §9 Phase 4 exit); writes to the COBOL backend frozen; COBOL kept readable as a hot rollback target for one quarter (SDD §9 Phase 5).                                                              |
| S13    | 25–26 | Decommission + closeout                              | Spring Boot gateways (`src/Z-OS-Connect-Customer-Services-Interface/`, `src/Z-OS-Connect-Payment-Interface/`), z/OS Connect artefacts (`src/zosconnect_artefacts/`), and BMS transactions (`OMEN`, `BNK1*`) retired; COBOL source archived under `legacy/cobol/` for historical reference; closeout pack delivered (lessons learned, BAU handover, runbooks); project formally closed at the Phase 3 gate. |

**Phase 3 exit criteria**

- OIDC auth enabled in production behind its feature flag; JWKS rotation rehearsed (NFR-05).
- OpenTelemetry traces visible end-to-end across the credit-agency fan-out and across both legs of `XFRFUN` (NFR-07).
- OCI image built reproducibly from a lockfile; deploy pipeline green (NFR-09).
- NFR-01 latency and throughput targets met on a representative production-like environment.
- 100 % production traffic served by Python for ≥ 1 week with SLOs equal to or better than the COBOL baseline (SDD §9 Phase 4).
- COBOL backend in read-only quarantine; one quarter elapsed with zero rollback events at the formal sign-off review.

---

## 6. Milestones

| ID  | Milestone                                                                          | Target Sprint | Target Week |
| --- | ---------------------------------------------------------------------------------- | ------------- | ----------- |
| M1  | Project kickoff & charter signed; Requirements §5 questions resolved               | S1            | Week 2      |
| M2  | PostgreSQL schemas (`banking.*`, `insurance.*`) live; Alembic baseline applied     | S2            | Week 4      |
| M3  | CBSA banking services passing FR-01…FR-05 tests in SDD §8 layout                   | S3            | Week 6      |
| M4  | **Phase 1 gate:** GenApp services passing FR-06; FR-07 abend log live; coverage ≥ 90 % | S4            | Week 8      |
| M5  | FastAPI routers publish full z/OS Connect contract (NFR-06)                        | S5            | Week 10     |
| M6  | Schemathesis contract suite green in CI                                            | S6            | Week 12     |
| M7  | Side-by-side runner reaches zero diff over a recorded window                       | S7            | Week 14     |
| M8  | **Phase 2 gate:** React UI repointed at FastAPI; two-week zero-diff window logged  | S8            | Week 16     |
| M9  | OIDC auth + OpenTelemetry + structured JSON logging delivered (NFR-05, NFR-07)     | S9            | Week 18     |
| M10 | OCI image + NFR-01 load-test sign-off                                              | S10           | Week 20     |
| M11 | 50 % traffic on Python with SLOs ≥ baseline                                        | S11           | Week 22     |
| M12 | 100 % traffic on Python for one full week; COBOL backend frozen                    | S12           | Week 24     |
| M13 | **Phase 3 gate:** legacy stack archived; project closeout pack delivered           | S13           | Week 26     |

---

## 7. Deliverables

### Per Phase

- **Phase 1 — Data Migration + Core Business Logic**
  - SDD §8 directory restructure of `python_app/` into `app/banking/`, `app/insurance/`, `app/shared/`, `app/db/`, `tests/`, `scripts/`.
  - Alembic migrations under `alembic/versions/` covering every entity in Requirements §4.1 and §4.2 (extending the existing `0001_initial_schema.py`).
  - `app/banking/services/` (carry-over from `python_app/app/services/`) and `app/insurance/services/` (new) implementing FR-01 … FR-07.
  - `app/banking/clients/credit_agency.py` with async fan-out + deterministic seed mode (FR-04).
  - `app/banking/repositories/counters.py` with `pg_advisory_xact_lock` named-counter equivalents (NFR-04).
  - `abnd_file` table + FastAPI exception handler that writes to it and emits a structured log event (FR-07).
  - `scripts/seed_banking.py` and `scripts/seed_insurance.py` (`BANKDATA` / `LGSETUP` equivalents) (FR-05).
  - Pytest corpus ≥ 90 % line coverage on `app/banking/` and `app/insurance/` (NFR-08); positive + negative case per FR (NFR-08).
  - `import-linter` configuration enforcing the SDD §8 boundary.
- **Phase 2 — API Layer + UI Integration**
  - `app/banking/routers.py` and `app/insurance/routers.py` matching the z/OS Connect contract byte-for-byte (NFR-06).
  - Generated FastAPI OpenAPI spec published in `doc/api/openapi.json`; every endpoint carries a `Replaces: <COBOL>` description (NFR-10).
  - Schemathesis contract test suite (`tests/e2e/test_react_contract.py`).
  - Side-by-side diff harness (script + dashboard) and a recorded two-week zero-diff window.
  - `.env` change committed to `src/bank-application-frontend/.env.example` documenting the FastAPI base URL.
- **Phase 3 — Hardening + Decommission**
  - `app/shared/auth.py` (OIDC, feature-flagged) (NFR-05).
  - OpenTelemetry instrumentation across services, repositories, and credit-agency clients (NFR-07).
  - Dockerfile + OCI image build + deploy pipeline (NFR-09).
  - Load-test report covering NFR-01 targets.
  - Updated `python_app/README.md` to reflect the SDD §8 layout and the final operating model.
  - Decommission runbook + archive PR moving COBOL sources under `legacy/cobol/`.
  - Closeout pack (lessons learned, BAU handover, on-call runbooks, final architecture sign-off).

### Cross-Cutting

- Living traceability table mapping every program in Requirements §1.3 / §1.4 to its Python module and to the FR it satisfies (NFR-10).
- Updated `doc/Software_Design_Document.md` cross-references where the implementation diverges from the SDD's recommendation, with the rationale logged in the decision log.
- Risk register and decision log maintained throughout.
- Operational dashboard (latency, error rate, side-by-side diff count, traffic split %).

---

## 8. Roles & Responsibilities (RACI)

| Activity                                            | Sponsor | PM   | Tech Lead | Python Dev | DevOps / Platform | QA  | React Dev | Security |
| --------------------------------------------------- | ------- | ---- | --------- | ---------- | ----------------- | --- | --------- | -------- |
| Charter & funding                                   | **A**   | R    | C         | I          | I                 | I   | I         | I        |
| Environment provisioning (Postgres, Docker, CI)     | I       | A    | C         | C          | **R**             | C   | I         | I        |
| SDD §8 restructure of `python_app/` (Phase 1)       | I       | A    | C         | **R**      | I                 | C   | I         | I        |
| CBSA service carry-over + extensions (Phase 1)      | I       | A    | C         | **R**      | I                 | C   | I         | I        |
| GenApp insurance module (Phase 1)                   | I       | A    | C         | **R**      | I                 | C   | I         | I        |
| Alembic migrations & seed scripts                   | I       | A    | C         | **R**      | C                 | C   | I         | I        |
| FastAPI routers + OpenAPI contract (Phase 2)        | I       | A    | C         | **R**      | I                 | C   | C         | I        |
| Schemathesis contract suite                         | I       | A    | C         | C          | I                 | **R** | C        | I        |
| Side-by-side runner (Phase 2)                       | I       | A    | C         | C          | C                 | **R** | I        | I        |
| React `.env` repoint + UI smoke (Phase 2)           | I       | A    | C         | I          | I                 | C   | **R**     | I        |
| OIDC auth + auth integration tests (Phase 3)        | I       | A    | C         | C          | C                 | C   | I         | **R**    |
| OpenTelemetry + structured logging (Phase 3)        | I       | A    | C         | **R**      | C                 | C   | I         | I        |
| OCI image + deploy pipeline (Phase 3)               | I       | A    | C         | C          | **R**             | C   | I         | I        |
| Load test against NFR-01 (Phase 3)                  | I       | A    | C         | C          | C                 | **R** | I        | I        |
| Production traffic ramp (Phase 3)                   | I       | A    | C         | C          | **R**             | C   | I         | I        |
| Decommission of COBOL / Spring Boot / z/OS Connect  | I       | A    | C         | C          | **R**             | C   | I         | C        |
| Phase-gate approvals                                | **A**   | R    | C         | C          | C                 | C   | C         | C        |

**Legend:** R = Responsible, A = Accountable, C = Consulted, I = Informed.

The legacy mainframe-specific roles from IPP v0.1 (CICS SA, Db2 DBA, COBOL Dev, Java Dev / WebSphere) are intentionally removed — none are needed for the Python migration. The COBOL backend is treated as a frozen read-only system through Phase 3; its operations are folded into the DevOps / Platform role for the rollback window only.

---

## 9. Resource Plan

### Human Resources

| Role                            | Allocation                                                                                                  |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Project Manager                 | 100 % across 6 months                                                                                       |
| Technical Lead                  | 100 % across 6 months                                                                                       |
| Python Developer × 2 (minimum), up to 3 | 100 % Phases 1 & 2, 75 % Phase 3                                                                       |
| DevOps / Platform Engineer      | 25 % Phase 1, 50 % Phase 2, 100 % Phase 3                                                                   |
| QA Engineer                     | 50 % Phase 1, 100 % Phase 2, 75 % Phase 3                                                                   |
| React / Front-end Developer     | 0 % Phase 1, ≤ 10 % (part-time) Phase 2 for the `.env` repoint and UI smoke testing, 0 % Phase 3            |
| Security Engineer (OIDC SME)    | 0 % Phases 1–2, 25 % Phase 3 (OIDC integration)                                                             |
| Executive Sponsor               | Phase-gate reviews                                                                                          |

### Infrastructure & Tooling

- **Runtime:** Python 3.12 on Linux/amd64. Single OCI image per the NFR-09 packaging target.
- **Database:** PostgreSQL 15+ — local Docker via `docker-compose.yml` for development; managed PostgreSQL for staging and production. SQLite (in-memory) is used in CI for fast unit/integration tests (as `python_app/tests/conftest.py` does today).
- **Dependency management:** `uv` (preferred) or `pip-tools` for deterministic lockfiles (NFR-09); requirements split into `requirements.txt` / `requirements-dev.txt` for now (matching `python_app/`).
- **Web / async stack:** FastAPI + Uvicorn; `httpx.AsyncClient` for credit-agency fan-out; `asyncio` for parallelism.
- **ORM / migrations:** SQLAlchemy + Alembic (already wired in `python_app/`).
- **Schemas:** Pydantic for all request/response models and typed configuration (`app/shared/config.py`).
- **Quality:** `ruff` for lint, `pytest` + `pytest-cov` for tests, `import-linter` for the SDD §8 boundary, Schemathesis for OpenAPI contract tests.
- **Observability:** OpenTelemetry SDK + `structlog` (or stdlib `logging` with JSON formatter).
- **Build / CI:** GitHub Actions (or equivalent) running `ruff`, `pytest`, `import-linter`, `alembic upgrade head` against a SQLite fixture, and Schemathesis. The existing Java / Maven build (`./mvnw`) stays in the pipeline as a regression check during Phases 1–2 (NFR-09).
- **Containerisation:** Docker (Compose for local; single Dockerfile for the OCI image).
- **Pre-commit:** `trailing-whitespace`, `end-of-file-fixer`, `check-yaml` from the repo's existing `.pre-commit-config.yaml`.
- **Source control:** This Git repository; one shared backlog with phase tags; PRs against `main` per `CONTRIBUTING.md`.

### Budget (high-level)

Detailed cost estimates are deferred to the Project Budget artifact. The IPP assumes standard internal labour rates for the staffing profile above, plus modest infrastructure spend for staging/production PostgreSQL and container hosting. No mainframe MIPS uplift is required. Tooling costs are limited to optional commercial OpenTelemetry / log aggregation tier; the OSS path is sufficient for v1.

---

## 10. Dependencies

### Internal

- Approval on the open Requirements questions (Q-1.1 … Q-3.2) before Sprint S2 — especially Q-2.1 (target relational store) and Q-2.3 (live data migration vs. seed-only for v1).
- The existing `python_app/` directory remains the seed for Phase 1; no parallel rewrite branch is sanctioned.
- The Carbon React UI in `src/bank-application-frontend/` accepts a backend URL via `.env` — confirmed in Sprint S1.
- The Java / Maven build (`./mvnw`) stays green throughout Phases 1–2 to keep the parallel-run reference usable.

### External

- PostgreSQL availability (local Docker image + managed instances for staging/production).
- Python 3.12 runtime availability on developer machines and CI.
- Docker registry (internal or hosted) for the OCI image (NFR-09).
- npm / Yarn registry availability for the Carbon React build during the Phase 2 UI smoke.
- The existing z/OS Connect swagger specs in `src/zosconnect_artefacts/apis/*/api-docs/swagger.json` as the **contract source-of-truth** for NFR-06.
- An OIDC identity provider (existing corporate IdP) for Phase 3 (NFR-05).

### Cross-Phase

- Phase 2 depends on Phase 1: routers require services and schemas.
- Phase 3 depends on Phase 2: hardening, traffic ramp, and decommission all assume contract parity with the COBOL backend.

---

## 11. Risks & Mitigations

The risk profile is now dominated by **behavioural-parity** and **integration** risks, not mainframe-availability risks. The mitigations below are sourced from the Software Design Document's Risks and Open Questions (SDD §10) and the Requirements document's open questions (Requirements §5).

| ID   | Risk                                                                                                          | Likelihood | Impact | Mitigation                                                                                                                                                                                                                                                                                                  |
| ---- | ------------------------------------------------------------------------------------------------------------- | ---------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-01 | Behavioural drift between COBOL and Python (rounding, date semantics, SQLCODE handling)                       | High       | High   | All money in `decimal.Decimal` / `NUMERIC(14,2)` (NFR-02). Side-by-side runner in Phase 2 (Sprint S7) compares per-request JSON responses; diff log reviewed daily; two consecutive zero-diff weeks are required before Phase 2 gate (SDD §10 row 1).                                                       |
| R-02 | Named-counter contention under load (replaces CICS named counters `NEWCUSNO`, `NEWACCNO`)                     | Medium     | High   | `app/banking/repositories/counters.py` uses Postgres advisory locks (`SELECT pg_advisory_xact_lock(...)`) with a cached sequence (NFR-04, SDD §7.3, SDD §10 row 3). Load test at 2× peak in Sprint S10 confirms no duplicates.                                                                                |
| R-03 | React UI has undocumented assumptions about the Spring Boot / z/OS Connect error envelope                     | Medium     | Medium | Phase 2 Schemathesis contract tests include negative-path cases; recorded production-shape traffic is replayed through the React UI against Python in Sprint S8 (SDD §10 row 5).                                                                                                                            |
| R-04 | Async credit-agency timeout semantics differ from CICS Async (FR-04)                                          | Medium     | Medium | `asyncio.gather` wrapped in `asyncio.wait_for(..., timeout=3.0)` to match the 3-second wait inside `CRECUST` (SDD §10 row 2). Deterministic seed mode in tests confirms identical averaged scores for identical inputs (NFR-08).                                                                              |
| R-05 | GenApp policy sub-type complexity (Endowment / House / Motor / Commercial) is mishandled                      | Medium     | Medium | SQLAlchemy single-table inheritance keyed on `policy_type` with Pydantic discriminated unions at the API boundary (SDD §10 row 4); contract tests per sub-type in Phase 2.                                                                                                                                  |
| R-06 | Legacy date format preservation on existing endpoints (DDMMYYYY for CBSA, YYYY-MM-DD for GenApp)              | Medium     | Medium | Default per Requirements §4.3 and Q-1.2: preserve legacy encodings on existing endpoints; use ISO 8601 on any new endpoint. Schemathesis tests anchor the date format in the contract.                                                                                                                       |
| R-07 | OIDC integration causes drop-in breakage for existing callers during cut-over                                 | Medium     | High   | NFR-05 requires the auth dependency to be **feature-flagged**; default off until the cut-over window; integration tests in Phase 3 verify both modes.                                                                                                                                                       |
| R-08 | Performance regression vs. NFR-01 targets (P50 ≤ 50 ms / P95 ≤ 250 ms read; ≥ 100 transfers/sec)              | Medium     | High   | Load test in Sprint S10; profile hot paths; per-domain connection pool quotas at `app/db/session.py` (SDD §4.3 weaknesses); back-pressure on the credit-agency fan-out.                                                                                                                                     |
| R-09 | Scope creep — pressure to rewrite the React UI or expand the REST contract during the migration               | Medium     | Medium | Frozen contract per NFR-06; strict change control after Phase 1 gate; new fields / breaking changes go to a v2 surface.                                                                                                                                                                                      |
| R-10 | Knowledge concentration in one or two engineers                                                               | Medium     | Medium | Pair-programming during Phase 1 carry-over; runbook updates each sprint; weekly knowledge-sharing session.                                                                                                                                                                                                  |
| R-11 | Data-reconciliation gaps if a one-shot live data migration is requested late (Q-2.3 reopened)                 | Low        | High   | Default for v1 is seed-only (Requirements §1.2); any change to live migration is a sponsor-approved change request that adds a dedicated ETL sprint.                                                                                                                                                        |
| R-12 | Pre-existing COBOL `SECURITY` MD5 password handling (Q-2.4) blocks GenApp customer auth in Phase 3            | Low        | Medium | Rollover plan agreed with security in Sprint S1 — Argon2id / bcrypt on first use with grandfathered MD5 for legacy rows; verified in Phase 3 integration tests (NFR-05).                                                                                                                                    |
| R-13 | Open question Q-3.1 (consolidate the five mock credit agencies vs. keep five distinct services) unresolved   | Low        | Low    | Default: keep five logical agency IDs behind one client per SDD §7.1, so the parallel-fan-out shape remains observable for teaching while the runtime cost stays low; revisit at Sprint S1 design review.                                                                                                   |

A live Risk Register will be maintained in the team workspace and reviewed at every sprint demo.

---

## 12. Quality & Acceptance Criteria

- **Definition of Done (DoD)** for any deliverable: code committed; peer-reviewed; tests added; `ruff` clean; `pytest` green at ≥ 90 % line coverage on the changed package; `import-linter` clean; runbook updated; CI green.
- **Definition of Ready (DoR)** for a sprint backlog item: acceptance criteria documented; FR / NFR back-reference cited; dependencies resolved; test data available; estimated.
- **Coding standards:** follow the conventions in the existing `python_app/`; do not modify generated artifacts; respect the existing `.gitignore` and `.gitattributes`.
- **Pre-commit hooks:** `trailing-whitespace`, `end-of-file-fixer`, and `check-yaml` from the repo's `.pre-commit-config.yaml` must pass on every commit.
- **Python-specific quality gates:**
  - `ruff check .` runs clean on `app/`, `tests/`, `scripts/`.
  - `pytest --cov=app --cov-fail-under=90` is enforced in CI (NFR-08).
  - `import-linter --config importlinter.cfg` enforces the SDD §8 boundary on every PR.
  - Schemathesis contract suite is green against the z/OS Connect swagger spec(s) before any router PR merges (NFR-06).
  - No `float` literals or `float()` casts in modules under `app/banking/services/transfer.py`, `app/banking/services/account.py`, or `app/insurance/services/policy.py` (NFR-02 spot-check).
- **Testing layers:**
  - Unit: services + repositories with in-memory SQLite (matching `python_app/tests/conftest.py` today).
  - Integration: full FastAPI app against PostgreSQL via Docker Compose; covers Alembic migrations and Pydantic schema serialisation.
  - Contract: Schemathesis against generated FastAPI OpenAPI plus the legacy z/OS Connect swagger.
  - End-to-end: Carbon React UI driving the Python backend through the standard browser flows.
  - Side-by-side: diff-based comparison of Python vs. COBOL responses for a recorded production-shape traffic sample (Phase 2).
  - Load: NFR-01 targets validated in Sprint S10.

---

## 13. Communication Plan

| Audience           | Channel                  | Cadence           | Owner     |
| ------------------ | ------------------------ | ----------------- | --------- |
| Project team       | Sprint stand-up          | Daily             | PM        |
| Project team       | Sprint planning & review | Every 2 weeks     | PM        |
| Project team       | Sprint retrospective     | Every 2 weeks     | PM        |
| Steering committee | Status report            | Monthly           | PM        |
| Sponsor            | Phase-gate review        | End of each phase | PM        |
| Wider org          | Newsletter / demo        | End of each phase | Tech Lead |
| Operations         | Change advisory board    | Per deployment    | DevOps    |

---

## 14. Governance & Approvals

- **Phase-gate model.** Each phase ends with a formal gate review where the sponsor confirms the exit criteria are met before the next phase starts. A "no-go" decision triggers a remediation plan and a follow-up gate review.
- **Change control.** Any scope, schedule, or cost change after the Phase 1 gate requires a written change request approved by the sponsor and PM. The REST contract (NFR-06) is frozen at Phase 2 gate — new fields go to a v2 surface.
- **Decision log.** All material decisions (architecture deviations from the SDD, data-format choices, OIDC posture, traffic ramp thresholds) are logged with date, owner, and rationale.
- **Issue escalation.** Sev 1 issues escalate to the sponsor within 4 business hours; Sev 2 within one business day.

---

## 15. Validation & Testing Strategy (Summary)

Detailed test plans are out of scope for the IPP but the following high-level approach is baselined:

1. **Phase 1 — Data Migration + Core Business Logic.** Pytest unit + integration tests against PostgreSQL locally and in-memory SQLite in CI (mirrors the current `python_app/tests/conftest.py`). FR-01 … FR-07 each have at least one positive and one negative test (NFR-08). Coverage gate ≥ 90 % on `app/banking/` and `app/insurance/` enforced in CI.
2. **Phase 2 — API Layer + UI Integration.** Schemathesis against the generated FastAPI OpenAPI spec and against the legacy z/OS Connect swagger (NFR-06). Side-by-side runner replays a recorded production-shape traffic sample against Python and against the COBOL backend; the JSON diff log is reviewed daily; two consecutive zero-diff weeks are required before the Phase 2 gate (SDD §9 Phase 2). React UI smoke against the FastAPI base URL covering the same flows documented in `etc/usage/libertyUI/doc/CBSA_Liberty_UI_User_Guide.md`.
3. **Phase 3 — Hardening + Decommission.** Load testing in Sprint S10 confirms the NFR-01 targets (P50 ≤ 50 ms / P95 ≤ 250 ms for reads; ≥ 100 transfers/sec for `XFRFUN`). OIDC integration tests cover both feature-flag states (NFR-05). OpenTelemetry traces are inspected end-to-end across the credit-agency fan-out and across both legs of `XFRFUN` (NFR-07). The Carbon React UI is exercised through the standard browser flows against the production-bound Python service.
4. **Cross-channel reconciliation.** For a curated set of CBSA and GenApp transactions, perform the same operation via the Carbon React UI and via the REST API and verify PostgreSQL observes an identical end-state, including PROCTRAN rows and `abnd_file` rows on negative-path tests.

---

## 16. Closeout

At the end of Sprint S13:

- Final UAT sign-off captured from business stakeholders.
- COBOL backend in read-only quarantine with a documented rollback procedure (effective for one quarter).
- Spring Boot gateways, z/OS Connect artefacts, and BMS transactions archived (`legacy/cobol/`); historical runbooks moved alongside.
- `python_app/README.md` and `doc/` updated to reflect the final operating model and the SDD §8 layout.
- BAU handover pack delivered to Operations (on-call runbook, dashboards, alerting, OCI image build/release procedure).
- Lessons-learned retrospective conducted; output filed alongside this plan.
- Project formally closed by the sponsor at the Phase 3 gate.

---

## 17. Appendices

### Appendix A — Mapping of Deliverables to Repository Artifacts

This appendix mirrors the SDD §7 mapping table and the `python_app/README.md` mapping table. The SDD remains the **authoritative source of truth** for the per-program mapping — this table summarises where the deliverables live in the repository.

| Deliverable                                                  | Repository Reference                                                                                                                       |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Authoritative architecture and program mapping               | `doc/Software_Design_Document.md` §7 (CBSA → `app/banking/`; GenApp → `app/insurance/`; cross-cutting)                                      |
| Authoritative functional + non-functional requirements       | `doc/COBOL_to_Python_Requirements.md` §2 (FR-01…FR-07), §3 (NFR-01…NFR-10), §4 (Data Model)                                                |
| As-is COBOL/CICS architecture                                | `doc/CBSA_Architecture_guide.md`                                                                                                           |
| Existing Python port (Phase 1 starting point)                | `python_app/` — FastAPI app (`app/main.py`), routers (`app/api/{customers,accounts,transfers,meta}.py`), models (`app/models/{account,control,customer,proctran}.py`), services (`app/services/{customer_service,account_service,transaction_service,support_service}.py`), Alembic baseline (`alembic/versions/0001_initial_schema.py`), seed (`app/db/seed.py`), tests (`tests/`) |
| Current Python ↔ COBOL mapping & business-rule list          | `python_app/README.md`                                                                                                                     |
| CBSA COBOL source (input to Phase 1 mapping)                 | `src/base/cobol_src/` (29 programs per SDD §3.2.1)                                                                                         |
| CBSA copybooks                                               | `src/base/cobol_copy/`                                                                                                                     |
| GenApp COBOL source (input to Phase 1 mapping)               | `cics-genapp/base/src/` (31 programs per SDD §3.2.2)                                                                                       |
| Legacy REST contract (source of truth for NFR-06)            | `src/zosconnect_artefacts/apis/*/api-docs/swagger.json`, `etc/usage/springBoot/doc/CBSA_Restful_API_guide.md`                              |
| Carbon React SPA (preserved as-is, repointed via `.env`)     | `src/bank-application-frontend/`                                                                                                           |
| Pre-existing Spring Boot REST gateways (to be decommissioned in Phase 3) | `src/Z-OS-Connect-Customer-Services-Interface/`, `src/Z-OS-Connect-Payment-Interface/`, `src/zosconnect_artefacts/`            |
| Legacy install / data DDL (input to Phase 1 schema design)   | `etc/install/base/db2jcl/`, `etc/install/base/installjcl/`                                                                                 |
| User guides (validation source for Phase 2 UI / contract)    | `etc/usage/libertyUI/`, `etc/usage/springBoot/`                                                                                            |

### Appendix B — Glossary (selected)

| Term                | Definition                                                                                                                                                |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FastAPI             | Asynchronous Python web framework with native Pydantic / OpenAPI integration. Hosts the Python migration target (`app/main.py`).                          |
| SQLAlchemy          | Python ORM used in `app/models/` (and post-restructure in `app/banking/models.py` / `app/insurance/models.py`).                                            |
| Alembic             | SQLAlchemy migrations tool. Versioned scripts live under `alembic/versions/`.                                                                              |
| PostgreSQL          | Target relational store (Requirements Q-2.1 default). Local via Docker; managed in staging/production. SQLite is used for fast CI tests.                  |
| Pydantic            | Typed schema library used for all request/response models and for env-driven configuration in `app/shared/config.py`.                                     |
| asyncio             | Python standard-library coroutine framework. Replaces CICS Async API for the `CRECUST` → `CRDTAGY1..5` fan-out (FR-04, SDD §7.3).                          |
| `httpx`             | Async HTTP client used by `app/banking/clients/credit_agency.py`.                                                                                          |
| `import-linter`     | Static analyser used to enforce the SDD §8 package boundary between `app.banking`, `app.insurance`, `app.shared`, and `app.db`.                            |
| Schemathesis        | Property-based contract testing tool that drives requests off an OpenAPI / swagger spec; used in Phase 2 to validate NFR-06.                              |
| OpenTelemetry       | Observability standard for traces / metrics / logs. Used to satisfy NFR-07 with cross-leg trace propagation through the credit-agency fan-out and `XFRFUN`. |
| OCI image           | Open Container Initiative image format. The deployable unit for the Python service (NFR-09).                                                              |
| `uv`                | Fast Python package manager with deterministic lockfiles (alternative: `pip-tools`). Drives NFR-09's "deterministic dependency pinning" requirement.       |
| Modular Monolith    | The recommended target architecture (SDD §4.3, §6) — a single FastAPI deployable partitioned into `banking/`, `insurance/`, and `shared/` packages with an enforced import boundary. |
| Side-by-side runner | Phase 2 diff harness that replays the same request against the Python service and the COBOL backend and compares the responses (SDD §9 Phase 2).           |

---

*End of document.*
