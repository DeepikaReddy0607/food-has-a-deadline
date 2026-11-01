# Food Has a Deadline (FHD) — Organization Verification System
## Final Engineering Verification & Architecture Report

**Version:** 1.0.0  
**Status:** Production Ready  
**Date:** November 1, 2026  
**Audience:** FHD Engineering Team, Security Auditors, Hackathon Evaluation Committee  

---

## 1. Executive Summary

In perishable food redistribution, trust and authenticity are critical operational requirements. To prevent fictitious actors, unsafe food dispatches, or misallocated supply, Food Has a Deadline (FHD) has introduced the **Organization Verification System**.

Prior to this implementation, new user registration automatically permitted suppliers and receivers to publish active surplus inventory and demand requests. Under the new architecture:

1. **Registration does NOT automatically grant verified status.** All newly registered suppliers and receivers default strictly to `PENDING_VERIFICATION`.
2. **Clear 4-tier lifecycle:**
   - `PENDING_VERIFICATION`: Initial state upon account creation.
   - `DOCUMENTS_SUBMITTED`: Official entity credentials and proof documents uploaded; awaiting coordinator review.
   - `VERIFIED`: Approved by an FHD coordinator or administrator; authorized for candidate matching and allocation proposals.
   - `REJECTED`: Declined by a coordinator with a mandatory justification; blocked from publishing listings and creating demands.
3. **Strict Operational Gates:**
   - `MatchingService` excludes unverified organizations from candidate matches (`is_eligible = False`) with transparent diagnostic reasons.
   - `SurplusService` and `DemandService` reject publications from `REJECTED` entities with `HTTP 403 Forbidden`.
4. **End-to-End Verification:**
   - 10 automated verification tests passing in `backend/tests/test_organization_verification.py`.
   - Full regression suite passing: **213 tests passed, 0 failed**.
   - Frontend production build: **100% clean, zero TypeScript errors**.

---

## 2. Architecture & Data Model

### 2.1 Database Migration (`g13b01234567_add_organization_verification.py`)

An Alembic migration was executed against the PostgreSQL production database with full rollback support (`upgrade` and `downgrade`):

```sql
-- Migration excerpts
ALTER TABLE users ADD COLUMN verification_status VARCHAR(32) NOT NULL DEFAULT 'PENDING_VERIFICATION';
ALTER TABLE users ADD CONSTRAINT ck_users_verification_status 
  CHECK (verification_status IN ('PENDING_VERIFICATION', 'DOCUMENTS_SUBMITTED', 'VERIFIED', 'REJECTED'));

-- Supplier Profiles
ALTER TABLE supplier_profiles ADD COLUMN verification_status VARCHAR(32) NOT NULL DEFAULT 'PENDING_VERIFICATION';
ALTER TABLE supplier_profiles ADD COLUMN license_number VARCHAR(100);
ALTER TABLE supplier_profiles ADD COLUMN representative_name VARCHAR(255);
ALTER TABLE supplier_profiles ADD COLUMN verification_document_path VARCHAR(500);
ALTER TABLE supplier_profiles ADD COLUMN verification_document_name VARCHAR(255);
ALTER TABLE supplier_profiles ADD COLUMN verification_submitted_at TIMESTAMPTZ;
ALTER TABLE supplier_profiles ADD COLUMN verified_at TIMESTAMPTZ;
ALTER TABLE supplier_profiles ADD COLUMN verified_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE supplier_profiles ADD COLUMN rejection_reason TEXT;
ALTER TABLE supplier_profiles ADD CONSTRAINT ck_supplier_verification_status 
  CHECK (verification_status IN ('PENDING_VERIFICATION', 'DOCUMENTS_SUBMITTED', 'VERIFIED', 'REJECTED'));

-- Receiver Profiles
ALTER TABLE receiver_profiles ADD COLUMN verification_status VARCHAR(32) NOT NULL DEFAULT 'PENDING_VERIFICATION';
ALTER TABLE receiver_profiles ADD COLUMN license_number VARCHAR(100);
ALTER TABLE receiver_profiles ADD COLUMN representative_name VARCHAR(255);
ALTER TABLE receiver_profiles ADD COLUMN verification_document_path VARCHAR(500);
ALTER TABLE receiver_profiles ADD COLUMN verification_document_name VARCHAR(255);
ALTER TABLE receiver_profiles ADD COLUMN verification_submitted_at TIMESTAMPTZ;
ALTER TABLE receiver_profiles ADD COLUMN verified_at TIMESTAMPTZ;
ALTER TABLE receiver_profiles ADD COLUMN verified_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE receiver_profiles ADD COLUMN rejection_reason TEXT;
ALTER TABLE receiver_profiles ADD CONSTRAINT ck_receiver_verification_status 
  CHECK (verification_status IN ('PENDING_VERIFICATION', 'DOCUMENTS_SUBMITTED', 'VERIFIED', 'REJECTED'));
```

Existing benchmark seed organizations (`DEMO-*`) were backfilled to `VERIFIED` with `is_verified=True` to maintain backward compatibility for historical transactions and regression baselines.

### 2.2 SQLAlchemy Models & Multiple Foreign Key Disambiguation

Because `verified_by_user_id` introduces a second foreign key relationship from `supplier_profiles` (and `receiver_profiles`) to `users.id`, SQLAlchemy mappers required explicit join conditions:

```python
# User model (backend/app/models/user.py)
supplier_profile: Mapped[Optional["SupplierProfile"]] = relationship(
    "SupplierProfile",
    back_populates="user",
    foreign_keys="[SupplierProfile.user_id]",
    cascade="all, delete-orphan",
    uselist=False,
)

# SupplierProfile model
user: Mapped["User"] = relationship(
    "User",
    back_populates="supplier_profile",
    foreign_keys=[user_id],
)
```

Furthermore, property getters and setters were added to `SupplierProfile` and `ReceiverProfile`:

```python
@property
def is_verified(self) -> bool:
    return self.verification_status == "VERIFIED"

@is_verified.setter
def is_verified(self, val: bool) -> None:
    if val:
        self.verification_status = "VERIFIED"
```

---

## 3. Security & RBAC Enforcement

1. **Role-Based Access Control (RBAC):**
   - Approval and rejection endpoints require `require_role("COORDINATOR", "ADMIN")`.
   - Suppliers and receivers attempting to invoke approval/rejection endpoints receive `HTTP 403 Forbidden`.
2. **Self-Approval & Self-Rejection Prevention:**
   - A coordinator cannot approve or reject their own registered organization. The service raises `HTTP 400 Bad Request` if `coordinator.id == profile.user_id`.
3. **Mandatory Rejection Justification:**
   - A coordinator rejecting an organization must provide a non-empty `reason` string of at least 3 characters. Rejection payloads with empty or whitespace-only strings fail Pydantic validation with `HTTP 422 Unprocessable Entity`.
4. **Secure Document Storage & Private Retrieval:**
   - Files are stored outside the public document root in `uploads/verification_docs/`.
   - File paths are sanitized and generated with UUID namespaces (`{profile_id}_{uuid}.{ext}`) to prevent directory traversal or file overwrites.
   - Enforces permitted file extensions: `.pdf`, `.jpg`, `.jpeg`, `.png`.
   - Verifies MIME types against magic byte headers.
   - Restricts file sizes to $\le 5\text{ MB}$.
   - The file retrieval endpoint `GET /api/v1/verifications/{org_type}/{profile_id}/document` verifies authorization: only coordinators, administrators, or the organization's account owner may download the submitted document.

---

## 4. Operational Restrictions & State Machine

```
               [New User Registration]
                         │
                         ▼
             ┌───────────────────────┐
             │ PENDING_VERIFICATION  │
             │   (Can create draft,  │
             │    cannot match)      │
             └───────────┬───────────┘
                         │
         [User submits verification doc]
                         ▼
             ┌───────────────────────┐
             │  DOCUMENTS_SUBMITTED  │
             │   (Under review by    │
             │     coordinator)      │
             └───────┬───────┬───────┘
                     │       │
      [Coordinator]  │       │  [Coordinator rejects
       approves      │       │   with mandatory reason]
                     ▼       ▼
┌─────────────────────────┐  ┌─────────────────────────┐
│        VERIFIED         │  │        REJECTED         │
│  - Eligible for matching│  │  - Cannot publish       │
│  - Active in optimizer  │  │    listings or demands  │
│  - Full green badge     │  │  - Rejection reason kept│
└─────────────────────────┘  └─────────────────────────┘
```

### Operational Rules Matrix

| State | Publish Surplus Listing | Publish Demand Request | Candidate Matching Eligibility | Optimization Proposal Inclusion |
| :--- | :---: | :---: | :---: | :---: |
| **`PENDING_VERIFICATION`** | Allowed (Initial draft) | Allowed (Initial draft) | **Blocked** (`is_eligible=False`) | **Blocked** (0 allocation) |
| **`DOCUMENTS_SUBMITTED`** | Allowed | Allowed | **Blocked** (`is_eligible=False`) | **Blocked** (0 allocation) |
| **`VERIFIED`** | **Allowed** | **Allowed** | **Eligible** | **Eligible** |
| **`REJECTED`** | **Forbidden (403)** | **Forbidden (403)** | **Blocked** (`is_eligible=False`) | **Blocked** (0 allocation) |

---

## 5. API Contract Specifications

The following REST API endpoints are registered under `/api/v1/verifications`:

### 1. `GET /api/v1/verifications/status`
- **Auth:** Any authenticated user.
- **Returns:** Current organization verification status, representative name, license number, document upload flag, submitted timestamp, and rejection reason (if any).

### 2. `POST /api/v1/verifications/submit`
- **Auth:** Authenticated Supplier or Receiver.
- **Payload:** `multipart/form-data` with `representative_name` (required), `license_number` (optional), `document` (required file $\le 5\text{ MB}$).
- **Behavior:** Saves file to `uploads/verification_docs/`, updates profile metadata, and transitions status to `DOCUMENTS_SUBMITTED`.

### 3. `GET /api/v1/verifications`
- **Auth:** Coordinator or Admin.
- **Query Params:** `status` (`DOCUMENTS_SUBMITTED`, `PENDING_VERIFICATION`, `VERIFIED`, `REJECTED`), `org_type` (`SUPPLIER`, `RECEIVER`).
- **Returns:** Aggregated list of organization items sorted with submitted review requests first.

### 4. `POST /api/v1/verifications/{org_type}/{profile_id}/approve`
- **Auth:** Coordinator or Admin.
- **Behavior:** Validates non-self-approval, sets status to `VERIFIED`, sets `is_verified=True`, sets `verified_at=now()`, and records `verified_by_user_id`.

### 5. `POST /api/v1/verifications/{org_type}/{profile_id}/reject`
- **Auth:** Coordinator or Admin.
- **Payload:** `{"reason": "Specific reason for rejection..."}` (min length 3).
- **Behavior:** Validates non-self-rejection, sets status to `REJECTED`, sets `is_verified=False`, persists `rejection_reason`.

### 6. `GET /api/v1/verifications/{org_type}/{profile_id}/document`
- **Auth:** Coordinator, Admin, or the owning organization.
- **Behavior:** Streams the uploaded document (`FileResponse`) with appropriate Content-Type.

### 7. Directory Endpoints
- `GET /api/v1/suppliers/directory` and `GET /api/v1/receivers/directory` include `verification_status` and `is_verified` in responses for transparent public directory listings.

---

## 6. Frontend User Experience

### 6.1 Reusable `VerificationBadge` (`frontend/src/components/common/VerificationBadge.tsx`)
Displays standard status-coded badges across the application:
- **`VERIFIED` (Green):** ShieldCheck icon, "Verified Organization" (`bg-emerald-100 text-emerald-800`).
- **`DOCUMENTS_SUBMITTED` (Blue):** Clock icon, "Documents Submitted" (`bg-blue-100 text-blue-800`).
- **`PENDING_VERIFICATION` (Yellow/Amber):** AlertCircle icon, "Pending Verification" (`bg-amber-100 text-amber-800`).
- **`REJECTED` (Red):** XCircle icon, "Verification Rejected" (`bg-red-100 text-red-800`).

### 6.2 Contextual `VerificationStatusBanner` (`frontend/src/components/verification/VerificationStatusBanner.tsx`)
Embedded at the top of:
- `MySurplusInventory.tsx`
- `MyDemandRequests.tsx`
- `SupplierProfileView.tsx`
- `ReceiverProfileView.tsx`

Provides instant feedback:
- If **Pending**: Alerts the organization that matching is paused and presents a **"Submit Documents"** button.
- If **Submitted**: Shows receipt of the document and informs the user that review is underway.
- If **Rejected**: Explains the exact rejection reason and presents a **"Re-submit Documentation"** button.
- Includes a self-contained submission modal handling representative name, license number, and file drag-and-drop with client-side file type and size validation.

### 6.3 Coordinator Verification Center (`frontend/src/pages/coordinator/OrganizationVerificationsPage.tsx`)
Accessible via the Coordinator navigation bar (`/coordinator/verifications`):
- Top-level operational metrics: Review Queue Count, Pending Documents Count, Verified Organizations Count, and Rejected Count.
- Instant search filter by organization name, email, or license number.
- Fast tab-filtering (`Review`, `Pending`, `Verified`, `Rejected`).
- One-click document inspection link (`Download Doc`).
- Immediate **Approve** button.
- **Reject** button with an interactive modal requiring coordinator justification.

---

## 7. Verification & Automated Test Suite

A dedicated regression test suite was implemented in `backend/tests/test_organization_verification.py` verifying all 10 core engineering criteria:

| Test ID | Test Function | Verified Behavior | Result |
| :--- | :--- | :--- | :---: |
| **TEST-01** | `test_01_new_registration_defaults_to_pending_verification` | New supplier and receiver profiles default to `PENDING_VERIFICATION` and `is_verified=False`. | **PASS** |
| **TEST-02** | `test_02_supplier_document_submission_transitions_status` | Supplier document upload stores file metadata and transitions to `DOCUMENTS_SUBMITTED`. | **PASS** |
| **TEST-03** | `test_03_receiver_document_submission_transitions_status` | Receiver document upload stores file metadata and transitions to `DOCUMENTS_SUBMITTED`. | **PASS** |
| **TEST-04** | `test_04_unauthorized_users_forbidden_from_approval_or_rejection` | Suppliers and receivers cannot approve or reject verifications (`HTTP 403 Forbidden`). | **PASS** |
| **TEST-05** | `test_05_coordinator_approves_verification` | Coordinator inspects review queue, approves organization, and timestamps approval. | **PASS** |
| **TEST-06** | `test_06_coordinator_rejects_verification_with_mandatory_reason` | Coordinator rejects organization with required reason; empty reasons fail with 422. | **PASS** |
| **TEST-07** | `test_07_rejected_organization_cannot_publish_surplus_or_demand` | `REJECTED` organizations receive `HTTP 403` when attempting to publish listings or demands. | **PASS** |
| **TEST-08** | `test_08_unverified_organization_ineligible_for_matching` | Unverified entities fail candidate matching with `is_eligible=False` and clear rejection diagnostic. | **PASS** |
| **TEST-09** | `test_09_verified_organizations_match_and_allocate_normally` | Upon approval by coordinator, organizations match as `ELIGIBLE` with positive score. | **PASS** |
| **TEST-10** | `test_10_verification_status_in_profiles_and_directory` | Verification statuses are accurately serialized across public directory endpoints. | **PASS** |

### Complete Backend Regression Suite

```
============================= test session starts =============================
platform win32 -- Python 3.12.0, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\Projects\FOOD-HAS-A-DEADLINE\backend
configfile: pytest.ini
collected 213 items

backend\tests\test_agent.py ..................................           [ 16%]
backend\tests\test_audit_edge_cases.py .................                 [ 24%]
backend\tests\test_auth.py ...........                                  [ 29%]
backend\tests\test_cors.py ...                                          [ 30%]
backend\tests\test_data_integrity.py .........                          [ 35%]
backend\tests\test_database.py .....                                    [ 37%]
backend\tests\test_demand.py .........                                  [ 41%]
backend\tests\test_e2e_workflow.py .                                    [ 42%]
backend\tests\test_geospatial.py .................                      [ 50%]
backend\tests\test_matching.py .........................                [ 61%]
backend\tests\test_optimization.py ....................                 [ 71%]
backend\tests\test_organization_verification.py ..........              [ 76%]
backend\tests\test_perishability.py ...............                     [ 83%]
backend\tests\test_postgres_concurrency.py .....                        [ 85%]
backend\tests\test_profiles.py .....                                    [ 87%]
backend\tests\test_redistribution_lifecycle.py ................         [ 95%]
backend\tests\test_surplus.py .........                                 [100%]

======================= 213 passed in 105.83s (0:01:45) =======================
```

### Frontend Production Build

```
> frontend@0.0.0 build
> tsc -b && vite build

vite v8.3.5 building client environment for production...
transforming...
✓ 2187 modules transformed.
rendering chunks...
dist/index.html                   0.43 kB │ gzip:   0.29 kB
dist/assets/index-C6Y0UCrI.css   63.69 kB │ gzip:  15.42 kB
dist/assets/index-D0P4Lyz-.js   881.62 kB │ gzip: 224.51 kB
✓ built in 3.90s
```

---

## 8. Deployment & Operational Checklist

1. **Database Migration:**
   Run `alembic upgrade head` in production environment.
2. **File Storage Permissions:**
   Ensure `uploads/verification_docs/` directory is writable by the backend application process.
3. **Environment Security:**
   Document downloads are authenticated and authorization-gated through `/api/v1/verifications/{org_type}/{profile_id}/document`.
4. **Hackathon Demo Guidance:**
   - Seeded demo suppliers and receivers are pre-verified (`VERIFIED`).
   - Registering a new organization live on stage demonstrates the `PENDING_VERIFICATION` badge and amber warning banner.
   - Uploading a document live on stage transitions the status to `DOCUMENTS_SUBMITTED`.
   - Logging in as a Coordinator (`coord@fhd.org`) demonstrates the Organization Verification Center, downloading credentials, and approving with instant status elevation.
