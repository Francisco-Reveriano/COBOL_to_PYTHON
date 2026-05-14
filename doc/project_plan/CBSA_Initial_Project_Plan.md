# CICS Bank Sample Application (CBSA) — Initial Project Plan

> SDLC Artifact: **Initial Project Plan (IPP)**
> Status: **Draft v0.1** — for stakeholder review
> Owner: Project Management Office (PMO)
> Cadence: 6 months, 3 phases, two-week sprints
> Last updated: 2026-05-14

---

## 1. Document Control

| Field            | Value                                          |
| ---------------- | ---------------------------------------------- |
| Project name     | CICS Bank Sample Application (CBSA) Rollout    |
| Project sponsor  | TBD (Executive Sponsor — Banking Modernization) |
| Project manager  | TBD                                            |
| Technical lead   | TBD                                            |
| SDLC stage       | Initiation / Planning                          |
| Document type    | Initial Project Plan (IPP)                     |
| Related artifacts | Architecture Guide (`doc/CBSA_Architecture_guide.md`), Install Guides (`etc/install/`), Usage Guides (`etc/usage/`) |
| Approval gate    | Phase-gate review at the end of each phase     |

### Revision History

| Version | Date       | Author | Notes                              |
| ------- | ---------- | ------ | ---------------------------------- |
| 0.1     | 2026-05-14 | PMO    | Initial draft for stakeholder review |

---

## 2. Executive Summary

This Initial Project Plan governs the end-to-end rollout of the CICS Bank Sample Application (CBSA) across a six-month delivery window, structured into three sequential phases that align to the installation model documented in this repository:

1. **Phase 1 — Base COBOL Foundation (Months 1–3, Mandatory).** Stand up the core banking platform: VSAM files, Db2 tables, COBOL load modules, BMS maps, CICS resource definitions, and the z/OS Connect base configuration. The phase exits when the BMS (3270) interface (`OMEN` transaction) executes the full set of banking transactions end-to-end against populated test data.
2. **Phase 2 — Carbon React Web UI (Months 4–5, Optional but planned).** Stand up the Liberty JVM server inside the CICS region, build the React/Carbon front-end, and deploy `webui-1.0.war` so that end users can perform banking functions from a modern browser-based interface.
3. **Phase 3 — Spring Boot REST Interfaces (Month 6, Optional but planned).** Build and deploy the Customer Services and Payment Spring Boot WARs into the Liberty JVM server, configure the z/OS Connect API definitions (`makepayment`, `inqcustz`, etc.), and validate the RESTful JSON contract against the CBSA backend.

The plan deliberately treats the optional phases as in-scope so the organization can demonstrate the full multi-channel architecture (3270 + Web + REST) on a single backend within the calendar year.

---

## 3. Goals and Objectives

### Business Goals
- Establish a reference banking platform that the organization can use as a teaching aid, testing harness, and conversation piece for application modernization discussions.
- Demonstrate that traditional CICS/COBOL workloads can be safely extended with Java, Liberty, and Spring Boot without disrupting the underlying transactional system of record.
- Provide a stable target environment for downstream modernization initiatives (e.g., Python migration, cloud connectivity, observability uplift).

### Technical Objectives
- Deploy a fully functional CBSA installation that passes every user guide in `etc/usage/`.
- Achieve data consistency across VSAM (`CUSTOMER`, `ABNDFILE`) and Db2 (`ACCOUNT`, `CONTROL`, `PROCTRAN`) for all test scenarios.
- Expose the CBSA backend through three integration channels: 3270 BMS, Carbon React web UI, and RESTful APIs over z/OS Connect.
- Establish CI hooks for the Java modules (`pom.xml` aggregator over `src/Z-OS-Connect-Customer-Services-Interface`, `src/Z-OS-Connect-Payment-Interface`, `src/webui`) and a repeatable build for the React front-end (`src/bank-application-frontend`).

### Success Metrics (KPIs)
| KPI                                            | Target                          |
| ---------------------------------------------- | ------------------------------- |
| Phase-gate sign-off on schedule                | 3 / 3 phases                    |
| Banking transactions passing UAT               | 100% of cases in user guides    |
| Mean time to deploy a new build (Java modules) | < 30 minutes from commit to CICS |
| Defect leakage to UAT (Sev 1/2)                | 0                               |
| Documentation coverage                         | Every installed component has a runbook entry |

---

## 4. Scope

### 4.1 In Scope
- All artifacts in this repository: COBOL sources (`src/base/cobol_src/`), copybooks (`src/base/cobol_copy/`), BMS maps (`src/base/bms_src/`), Java modules in `src/`, z/OS Connect artifacts in `src/zosconnect_artefacts/`, and install/usage documentation in `etc/`.
- Setup of the CICS TS 6.1+ region, Db2 v12+ subsystem, z/OS Connect server, and Liberty JVM server required by the install guides.
- Build and packaging of `webui-1.0.war` and the two Spring Boot WARs.
- CSD updates, named counter setup, and `server.xml` updates as documented in `etc/install/base/doc/README.md`.
- Functional and integration testing through each of the four interfaces (BMS, Carbon React, Customer Services, Payment).

### 4.2 Out of Scope
- Production hardening (high availability, disaster recovery, capacity planning beyond a single CICS region).
- Migration of the COBOL workload to another language or runtime (e.g., Python). That work is tracked separately and may consume the platform delivered by this project as its baseline.
- Long-term operational support beyond the project closeout (transitions to BAU at Phase 3 exit).
- Mainframe procurement, licensing, or capacity uplifts. The plan assumes existing CICS / Db2 / z/OS Connect capacity is available.
- Integration with downstream channels not present in this repo (e.g., mobile apps, third-party payment networks).

### 4.3 Assumptions
- A CICS TS region at v6.1 (with APAR PH60795 applied) or later is available for the duration of the project.
- A Db2 subsystem at v12 or later is available, with administrative access for `BIND PACKAGE`, table creation, and data load.
- A z/OS Connect server is installed and reachable; default port assumption `30701` (HTTP) and `30702` (HTTPS) per `etc/install/base/doc/README.md`.
- Java 17 and a Maven wrapper (`mvnw`) are available on every build host; Yarn is available for the React build.
- The team has TSO/ISPF access, FTP/SFTP to the CICS LPAR, and authority to submit JCL and update DFHCSD.

### 4.4 Constraints
- Phase 1 must complete before Phases 2 and 3 — the optional interfaces depend on the base COBOL backend.
- Two-week sprint cadence is fixed; phase boundaries align with sprint boundaries.
- No changes to the published banking business logic (the COBOL programs are treated as authoritative); modernization phases must integrate, not rewrite.

---

## 5. Phased Delivery Timeline

```
Month:   1     2     3     4     5     6
Sprint:  1  2  3  4  5  6  7  8  9 10 11 12 13
Phase:  [-------Phase 1-------][--Phase 2--][P3]
```

Two-week sprints. Phase 1 spans Sprints 1–6 (12 weeks). Phase 2 spans Sprints 7–10 (8 weeks). Phase 3 spans Sprints 11–13 (6 weeks). Sprint 13 doubles as the project closeout sprint.

### 5.1 Phase 1 — Base COBOL Installation (Mandatory) — Months 1–3

**Phase goal:** Stand up the CBSA backend on CICS such that the BMS interface (`OMEN`) can execute every banking transaction against populated VSAM and Db2 data.

| Sprint | Weeks | Focus                                  | Key Deliverables                                                                                                    |
| ------ | ----- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| S1     | 1–2   | Mobilization & environment readiness   | Project kickoff, RACI signed, CICS/Db2/z/OS Connect access confirmed, libraries allocated on the host LPAR          |
| S2     | 3–4   | Data layer foundation                  | VSAM clusters defined for `CUSTOMER` and `ABNDFILE`; Db2 schema for `ACCOUNT`, `CONTROL`, `PROCTRAN` created and bound |
| S3     | 5–6   | COBOL build pipeline                   | All 24 programs from `src/base/cobol_src/` (e.g., `BNK1CAC.cbl`, `CREACC.cbl`) compiled, link-edited, and load modules placed in the CICS load library via `etc/install/base/buildjcl` and `linkeditjcl` |
| S4     | 7–8   | BMS maps & CICS resource definitions   | All 9 maps from `src/base/bms_src/` (e.g., `BNK1ACC.bms`, `BNK1MAI.bms`) assembled; DFHCSD updated via `etc/install/base/installjcl`; named counter and CICS resources installed |
| S5     | 9–10  | Data population & z/OS Connect base    | `BANKDATA` populates VSAM and Db2 with deterministic test data; z/OS Connect `server.xml` reconciled to project port assignments |
| S6     | 11–12 | System integration test & Phase 1 gate | OMEN BMS interface validated end-to-end against the `etc/usage/base/doc/CBSA_BMS_User_Guide.md` checklist; Phase 1 closeout review and gate approval |

**Phase 1 exit criteria**
- BMS interface executes every banking function listed in the base user guide with zero Sev 1/2 defects open.
- Data consistency tests pass: VSAM and Db2 record counts and key relationships verified after a full transaction run.
- Backout plan documented and rehearsed.
- Operational runbook for the base install merged to `etc/install/base/` is current.

### 5.2 Phase 2 — Carbon React UI Installation (Optional) — Months 4–5

**Phase goal:** Deliver a modern browser-based banking interface that reuses the Phase 1 backend through a Liberty JVM server.

| Sprint | Weeks | Focus                                  | Key Deliverables                                                                                                    |
| ------ | ----- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| S7     | 13–14 | Liberty JVM server inside CICS         | `CBSAWLP` Liberty JVM server defined and started inside the CICS region; `server.xml` updates merged per `etc/install/carbonReactUI/doc/...` |
| S8     | 15–16 | Web front-end build                    | `src/bank-application-frontend` builds cleanly with `yarn install && yarn build`; static assets copied into `src/webui/WebContent/static` via `updateWebUI.sh` |
| S9     | 17–18 | WAR packaging & deployment             | `mvn clean package` produces `webui-1.0.war`; WAR deployed to `CBSAWLP`; smoke test of static UI shell passes      |
| S10    | 19–20 | Functional/integration test & Phase 2 gate | Carbon React UI validated against `etc/usage/libertyUI/doc/CBSA_Liberty_UI_User_Guide.md`; Phase 2 closeout review and gate approval |

**Phase 2 exit criteria**
- Carbon React UI hosts the documented banking flows (account view, transfer, enhanced search) over the Phase 1 backend.
- Build is reproducible via `build.sh` end-to-end on a clean clone.
- Liberty JVM server starts cleanly with the CICS region.
- No regression in Phase 1 BMS functionality.

### 5.3 Phase 3 — Spring Boot REST Interfaces (Optional) — Month 6

**Phase goal:** Expose the CBSA backend through Spring Boot–based REST APIs deployed alongside the Carbon React UI in the Liberty JVM server, fronted by z/OS Connect.

| Sprint | Weeks | Focus                                  | Key Deliverables                                                                                                    |
| ------ | ----- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| S11    | 21–22 | Customer Services interface            | `src/Z-OS-Connect-Customer-Services-Interface` builds and deploys; CS endpoints respond from Liberty                |
| S12    | 23–24 | Payment interface                      | `src/Z-OS-Connect-Payment-Interface` builds and deploys; Payment endpoints respond from Liberty                     |
| S13    | 25–26 | z/OS Connect APIs, UAT, closeout       | API definitions (`makepayment`, `inqcustz`, etc.) registered with z/OS Connect; full RESTful API validation against `etc/usage/springBoot/doc/CBSA_Restful_API_guide.md`; UAT sign-off; project closeout |

**Phase 3 exit criteria**
- All REST endpoints in the API guide return contractually correct responses under happy-path and negative-path tests.
- The CS and Payment user guides (`etc/usage/springBoot/doc/...`) execute end-to-end.
- Project closeout deliverables produced (lessons learned, runbook updates, BAU handover pack).

---

## 6. Milestones

| ID  | Milestone                                       | Target Sprint | Target Week |
| --- | ----------------------------------------------- | ------------- | ----------- |
| M1  | Project kickoff & charter signed                | S1            | Week 1      |
| M2  | CICS / Db2 / z/OS Connect access confirmed      | S1            | Week 2      |
| M3  | VSAM and Db2 schema in place                    | S2            | Week 4      |
| M4  | All COBOL load modules built                    | S3            | Week 6      |
| M5  | DFHCSD updated; BMS maps installed              | S4            | Week 8      |
| M6  | Base data populated; z/OS Connect base online   | S5            | Week 10     |
| M7  | **Phase 1 gate: BMS interface signed off**      | S6            | Week 12     |
| M8  | Liberty JVM server (`CBSAWLP`) live in CICS     | S7            | Week 14     |
| M9  | Reproducible React build                        | S8            | Week 16     |
| M10 | `webui-1.0.war` deployed                        | S9            | Week 18     |
| M11 | **Phase 2 gate: Carbon React UI signed off**    | S10           | Week 20     |
| M12 | Customer Services interface live                | S11           | Week 22     |
| M13 | Payment interface live                          | S12           | Week 24     |
| M14 | **Phase 3 gate: REST APIs + project closeout**  | S13           | Week 26     |

---

## 7. Deliverables

### Per Phase
- **Phase 1:** Populated VSAM and Db2 stores; CICS load library populated with all 24 COBOL load modules; DFHCSD updated; BMS maps installed; z/OS Connect base `server.xml`; OMEN demo evidence pack; Phase 1 gate deck.
- **Phase 2:** `CBSAWLP` Liberty JVM server configuration; built `webui-1.0.war`; updated React `package.json` lockfile checked in; Carbon React UI demo evidence pack; Phase 2 gate deck.
- **Phase 3:** Customer Services and Payment WARs; registered z/OS Connect API definitions; Postman/Newman collection for the REST API; UAT evidence; project closeout pack (lessons learned, BAU handover, runbooks).

### Cross-Cutting
- Updated runbooks in `etc/install/` for each interface installed.
- Test plan and test results matrix referencing each user guide in `etc/usage/`.
- Risk register and decision log maintained throughout.
- Operational dashboard (CICS region health, Liberty JVM health, z/OS Connect availability) — even if lightweight.

---

## 8. Roles & Responsibilities (RACI)

| Activity                              | Sponsor | PM   | Tech Lead | CICS SA | Db2 DBA | COBOL Dev | Java Dev | React Dev | QA   | Ops  |
| ------------------------------------- | ------- | ---- | --------- | ------- | ------- | --------- | -------- | --------- | ---- | ---- |
| Charter & funding                     | **A**   | R    | C         | I       | I       | I         | I        | I         | I    | I    |
| Environment provisioning              | I       | A    | R         | **R**   | **R**   | C         | C        | C         | C    | C    |
| VSAM / Db2 setup (Phase 1)            | I       | A    | C         | **R**   | **R**   | C         | I        | I         | C    | C    |
| COBOL build & link (Phase 1)          | I       | A    | C         | C       | I       | **R**     | I        | I         | C    | C    |
| BMS map assembly & CSD updates        | I       | A    | C         | **R**   | I       | C         | I        | I         | C    | C    |
| Base z/OS Connect setup               | I       | A    | C         | **R**   | I       | C         | C        | I         | C    | C    |
| Liberty JVM server config (Phase 2)   | I       | A    | C         | **R**   | I       | I         | C        | C         | C    | C    |
| React build (Phase 2)                 | I       | A    | C         | I       | I       | I         | C        | **R**     | C    | I    |
| WAR deployment (Phases 2 & 3)         | I       | A    | C         | C       | I       | I         | **R**    | C         | C    | C    |
| Spring Boot interfaces (Phase 3)      | I       | A    | C         | C       | I       | I         | **R**    | C         | C    | C    |
| z/OS Connect APIs (Phase 3)           | I       | A    | C         | **R**   | I       | I         | C        | I         | C    | C    |
| Functional/UAT testing                | I       | A    | C         | C       | C       | C         | C        | C         | **R** | I    |
| Phase-gate approvals                  | **A**   | R    | C         | C       | C       | C         | C        | C         | C    | C    |
| Production handover (closeout)        | **A**   | R    | C         | C       | C       | C         | C        | C         | C    | **R** |

**Legend:** R = Responsible, A = Accountable, C = Consulted, I = Informed.

---

## 9. Resource Plan

### Human Resources
| Role                       | Allocation                                |
| -------------------------- | ----------------------------------------- |
| Project Manager            | 100% across 6 months                      |
| Technical Lead             | 100% across 6 months                      |
| CICS Systems Administrator | 100% Phase 1, 50% Phases 2–3              |
| Db2 DBA                    | 50% Phase 1, on-call thereafter           |
| COBOL Developer (x1–2)     | 100% Phase 1, on-call thereafter          |
| Java Developer (x1–2)      | 25% Phase 1, 100% Phases 2–3              |
| React/Front-end Developer  | 0% Phase 1, 100% Phase 2, 25% Phase 3     |
| QA Engineer                | 25% Phase 1 ramping to 100% in each gate  |
| Operations / Release       | 25% throughout                            |
| Executive Sponsor          | Phase-gate reviews                        |

### Infrastructure & Tooling
- **Mainframe:** CICS TS 6.1+ region (APAR PH60795 applied), Db2 v12+ subsystem (`DBCG` in install docs), z/OS Connect server (USS at `/var/zosconnect/v3r0/servers/defaultServer/...`).
- **Build hosts:** Java 17 with the included Maven wrapper (`./mvnw`), Node.js + Yarn for the React build, GnuCOBOL or vendor compiler only if a non-mainframe sandbox is used for unit-level smoke tests.
- **Source control:** This Git repository.
- **CI/CD:** Job to run `./build.sh` (React build + `updateWebUI.sh` + `mvn clean package`) on every PR; mainframe-side build via the JCL in `etc/install/base/buildjcl` and `linkeditjcl`.
- **Test tooling:** 3270 emulator (e.g., x3270, IBM PCOMM) for Phase 1; modern browser for Phase 2; Postman/Newman or `curl` for Phase 3 RESTful tests.
- **Collaboration:** Issue tracker per the `CONTRIBUTING.md` guidance; one shared backlog with phase tags.

### Budget (high-level)
Detailed cost estimates are deferred to the Project Budget artifact. The IPP assumes pre-existing mainframe capacity (no incremental MIPS purchase) and standard internal labor rates for the staffing profile above. Tooling costs are limited to Carbon Design System usage (already permissively licensed) and any commercial 3270 emulator licenses the team prefers.

---

## 10. Dependencies

### Internal
- Availability of the CICS region, Db2 subsystem, and z/OS Connect server before Sprint S2.
- Access for the build team to update the CICS load library and submit JCL.
- Operations team availability for `CBSAWLP` Liberty JVM server creation at the start of Phase 2.

### External
- IBM CICS TS BOM (`com.ibm.cics.ts.bom` v6.1) availability via Maven (resolved transparently by `mvnw`).
- Carbon Design System npm packages (`@carbon/react` and friends) resolvable from the configured npm registry.
- Yarn registry availability for `yarn install` during Phase 2.

### Cross-Phase
- Phase 2 depends on Phase 1 (Liberty JVM server connects to the CICS resources installed in Phase 1).
- Phase 3 depends on Phase 1 (REST interfaces invoke the COBOL programs) and on Phase 2 (Spring Boot WARs deploy into the same `CBSAWLP` Liberty JVM server).

---

## 11. Risks & Mitigations

| ID   | Risk                                                                                   | Likelihood | Impact | Mitigation                                                                                                                                                                       |
| ---- | -------------------------------------------------------------------------------------- | ---------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-01 | CICS region not available on time                                                      | Medium     | High   | Confirm access in Sprint S1; escalate to sponsor immediately if blocked; pre-stage a sandbox region as a contingency                                                             |
| R-02 | APAR PH60795 missing from the CICS TS 6.1 region                                       | Low        | High   | Validate apply status during Sprint S1 environment readiness; engage IBM support early if a fix is needed                                                                       |
| R-03 | DFHCSD updates conflict with existing CICS resources                                   | Medium     | Medium | Run the install JCL in a non-production region first; use the rollback JCL in `etc/install/base/installjcl`                                                                     |
| R-04 | Db2 BIND failures during Phase 1                                                       | Medium     | Medium | Build a Db2 dry-run checklist; coordinate with the DBA in Sprint S2; rebind in lower environments first                                                                          |
| R-05 | React build breaks due to npm/Yarn supply-chain churn                                  | Medium     | Low    | Pin versions through `yarn.lock`; run `build.sh` end-to-end in CI on every PR; cache `node_modules` to reduce variance                                                          |
| R-06 | Port collision on z/OS Connect (default 30701/30702)                                   | Low        | Medium | Confirm port allocation in Sprint S1; document the chosen ports in the runbook                                                                                                  |
| R-07 | Liberty JVM server fails to start inside CICS                                          | Medium     | High   | Stand up `CBSAWLP` in a non-production region first; capture diagnostic logs; pair the CICS SA with the Java developer during Sprint S7                                         |
| R-08 | z/OS Connect API authentication/authorization gaps surface during Phase 3              | Medium     | Medium | Decide authentication posture (basic auth, OAuth, certificate) in Sprint S11; align with security team early                                                                     |
| R-09 | Knowledge concentration in one or two engineers                                        | Medium     | Medium | Pair programming and runbook updates each sprint; weekly knowledge-sharing session                                                                                              |
| R-10 | Scope creep from optional phases extending past 6 months                               | Medium     | Medium | Strict change control: scope changes after Phase 1 gate require sponsor approval; defer non-essential work to a follow-on initiative                                            |
| R-11 | Data drift between VSAM and Db2 during testing                                         | Low        | High   | Run consistency checks at the end of each sprint; automate with a reusable verification job                                                                                      |
| R-12 | Test environments shared with other workloads                                          | Medium     | Medium | Reserve windows for CBSA testing; coordinate with operations on a published test calendar                                                                                        |

A live Risk Register will be maintained in the team workspace and reviewed at every sprint demo.

---

## 12. Quality & Acceptance Criteria

- **Definition of Done (DoD)** for any deliverable: code (or JCL) committed; peer-reviewed; runbook updated; relevant section of the user guide rehearsed; CI green where applicable.
- **Definition of Ready (DoR)** for a sprint backlog item: acceptance criteria documented; dependencies resolved; test data available; estimated.
- **Coding standards:** Follow the conventions in the existing repository; do not modify generated artifacts; respect the `.gitignore` and `.gitattributes`.
- **Pre-commit hooks:** `trailing-whitespace`, `end-of-file-fixer`, and `check-yaml` from `.pre-commit-config.yaml` must pass on every commit.
- **Testing layers:**
  - Unit: applicable to the Java modules.
  - Component / integration: exercised through the BMS interface for Phase 1, the Carbon React UI for Phase 2, and the REST APIs for Phase 3.
  - UAT: scripted against `etc/usage/` user guides for each interface.

---

## 13. Communication Plan

| Audience            | Channel                  | Cadence            | Owner |
| ------------------- | ------------------------ | ------------------ | ----- |
| Project team        | Sprint stand-up          | Daily              | PM    |
| Project team        | Sprint planning & review | Every 2 weeks      | PM    |
| Project team        | Sprint retrospective     | Every 2 weeks      | PM    |
| Steering committee  | Status report            | Monthly            | PM    |
| Sponsor             | Phase-gate review        | End of each phase  | PM    |
| Wider org           | Newsletter / demo        | End of each phase  | Tech Lead |
| Operations          | Change advisory board    | Per deployment     | Ops   |

---

## 14. Governance & Approvals

- **Phase-gate model.** Each phase ends with a formal gate review where the sponsor confirms exit criteria are met before the next phase starts. A "no-go" decision triggers a remediation plan and a follow-up gate review.
- **Change control.** Any scope, schedule, or cost change after the Phase 1 gate requires a written change request approved by the sponsor and PM.
- **Decision log.** All material decisions (architecture, sequencing, deferred scope) are logged with date, owner, and rationale.
- **Issue escalation.** Sev 1 issues escalate to the sponsor within 4 business hours; Sev 2 within one business day.

---

## 15. Validation & Testing Strategy (Summary)

Detailed test plans are out of scope for the IPP but the following high-level approach is baselined:

1. **Phase 1 — Base COBOL:** execute every scenario from `etc/usage/base/doc/CBSA_BMS_User_Guide.md` via the OMEN transaction; assert VSAM / Db2 consistency after each run.
2. **Phase 2 — Carbon React UI:** execute every scenario from `etc/usage/libertyUI/doc/CBSA_Liberty_UI_User_Guide.md`; cross-check that Phase 1 BMS flows still pass (regression).
3. **Phase 3 — Spring Boot interfaces:** execute the Customer Services and Payment user guides; run the REST suite against `etc/usage/springBoot/doc/CBSA_Restful_API_guide.md` happy and negative paths; validate JSON contracts.
4. **Cross-channel reconciliation:** for a curated set of transactions, perform the same operation via BMS, Carbon React, and REST and verify Db2 / VSAM observe an identical end-state.

---

## 16. Closeout

At the end of Sprint S13:
- Final UAT sign-off captured from business stakeholders.
- Runbooks under `etc/install/` and `etc/usage/` confirmed current.
- BAU handover pack delivered to Operations.
- Lessons learned retrospective conducted; output filed alongside this plan.
- Project formally closed by the sponsor at the Phase 3 gate.

---

## 17. Appendices

### Appendix A — Mapping of Deliverables to Repository Artifacts

| Deliverable                          | Repository Reference                                                                 |
| ------------------------------------ | ------------------------------------------------------------------------------------- |
| Base install runbook                 | `etc/install/base/doc/README.md`                                                      |
| Build JCL                            | `etc/install/base/buildjcl/`                                                          |
| Db2 JCL                              | `etc/install/base/db2jcl/`                                                            |
| Install JCL (CSD, named counter)     | `etc/install/base/installjcl/`                                                        |
| Link-edit JCL                        | `etc/install/base/linkeditjcl/`                                                       |
| COBOL programs (24)                  | `src/base/cobol_src/`                                                                 |
| Copybooks                            | `src/base/cobol_copy/`                                                                |
| BMS maps (9)                         | `src/base/bms_src/`                                                                   |
| z/OS Connect base configuration      | `etc/install/base/zosconnectserver/` (referenced by base install README)              |
| Carbon React UI install guide        | `etc/install/carbonReactUI/doc/CBSA_Carbon_React_UI_installation_deployment_guide.md` |
| React front-end source               | `src/bank-application-frontend/`                                                      |
| WebUI Jakarta EE project             | `src/webui/`                                                                          |
| Spring Boot install guide            | `etc/install/springBootUI/doc/CBSA_Deploying_the_Payment_Customer_Services_Springboot_apps.md` |
| Customer Services Spring Boot module | `src/Z-OS-Connect-Customer-Services-Interface/`                                       |
| Payment Spring Boot module           | `src/Z-OS-Connect-Payment-Interface/`                                                 |
| z/OS Connect artefacts               | `src/zosconnect_artefacts/`                                                           |
| Aggregator build                     | `pom.xml`, `build.sh`, `build.bat`                                                    |
| User guides (validation source)      | `etc/usage/base/`, `etc/usage/libertyUI/`, `etc/usage/springBoot/`                    |

### Appendix B — Glossary (selected)

| Term            | Definition                                                                                       |
| --------------- | ------------------------------------------------------------------------------------------------ |
| BMS             | Basic Mapping Support — formats 3270 terminal screens.                                            |
| CSD / DFHCSD    | CICS System Definition file — holds CICS resource definitions.                                    |
| KSDS            | VSAM Key-Sequenced Data Set; used by the `CUSTOMER` file.                                         |
| Liberty JVM     | WebSphere Liberty profile running inside the CICS region as a JVM server (`CBSAWLP`).             |
| Named Counter   | CICS facility for generating unique IDs.                                                          |
| OMEN            | The primary CICS transaction used to invoke the BMS interface.                                    |
| Syncpointing    | Unit-of-work management coordinating Db2 and VSAM.                                                |
| z/OS Connect    | Middleware that exposes CICS programs as REST APIs.                                               |

---

*End of document.*
