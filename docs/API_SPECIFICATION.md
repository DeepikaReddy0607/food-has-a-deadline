# FOOD HAS A DEADLINE (FHD) — API SPECIFICATION

> **API Standard:** RESTful JSON / OpenAPI 3.1  
> **Base Path:** `/api/v1`  
> **Status:** Architecture Specification (Endpoints are defined here; implementation belongs to later modules)

---

## 1. Authentication & Security Headers

All protected endpoints require the HTTP `Authorization` header containing a valid Bearer JWT:
```http
Authorization: Bearer <access_token>
```

Standard error envelope:
```json
{
  "error": {
    "code": "STRING_ERROR_CODE",
    "message": "Human-readable explanation of error.",
    "details": {}
  }
}
```

---

## 2. API Endpoints Catalog

### 2.1 Authentication & Identity (`/auth`)

#### `POST /api/v1/auth/register`
* **Purpose:** Register a new user account (Supplier or Receiver).
* **Auth:** Public.
* **Request Body:**
  ```json
  {
    "email": "coordinator@shelter.org",
    "password": "StrongPassword123!",
    "role": "RECEIVER",
    "organization_name": "Hope Community Kitchen",
    "contact_phone": "+1-555-0199",
    "address": "123 Civic Center Way",
    "latitude": 37.7749,
    "longitude": -122.4194
  }
  ```
* **Success Response (`201 Created`):**
  ```json
  {
    "user_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "email": "coordinator@shelter.org",
    "role": "RECEIVER",
    "message": "Account registered successfully."
  }
  ```
* **Errors:** `400 Bad Request` (Email already registered), `422 Unprocessable Entity` (Weak password, invalid coordinates).

---

#### `POST /api/v1/auth/login`
* **Purpose:** Authenticate credentials and obtain JWT access token.
* **Auth:** Public.
* **Request Body (OAuth2 Form / JSON):**
  ```json
  {
    "username": "coordinator@shelter.org",
    "password": "StrongPassword123!"
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "expires_in_minutes": 60,
    "user": {
      "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "email": "coordinator@shelter.org",
      "role": "RECEIVER"
    }
  }
  ```
* **Errors:** `401 Unauthorized` (Invalid credentials), `403 Forbidden` (Account disabled).

---

#### `GET /api/v1/auth/me`
* **Purpose:** Fetch current authenticated user identity and associated profile.
* **Auth:** Bearer Token (Any active role).
* **Success Response (`200 OK`):**
  ```json
  {
    "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "email": "coordinator@shelter.org",
    "role": "RECEIVER",
    "profile": {
      "id": "c3a1e0b5-1c88-4903-8d2e-3362174dfb67",
      "organization_name": "Hope Community Kitchen",
      "latitude": 37.7749,
      "longitude": -122.4194
    }
  }
  ```

---

### 2.2 Supplier Management (`/suppliers`)

#### `GET /api/v1/suppliers/profile`
* **Purpose:** Retrieve supplier facility profile and operating hours.
* **Auth:** Supplier or Admin.
* **Success Response (`200 OK`):**
  ```json
  {
    "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "organization_name": "Metro Fresh Supermarket",
    "contact_phone": "+1-555-0144",
    "facility_type": "SUPERMARKET",
    "address": "456 Market St, Cityville",
    "latitude": 37.7833,
    "longitude": -122.4167,
    "operating_hours": {
      "mon_fri": "07:00-22:00",
      "sat_sun": "08:00-20:00"
    }
  }
  ```

---

### 2.3 Receiver Management (`/receivers`)

#### `GET /api/v1/receivers/profile`
* **Purpose:** Retrieve receiver organization profile, intake capacities, and cold-chain hardware.
* **Auth:** Receiver or Admin.
* **Success Response (`200 OK`):**
  ```json
  {
    "id": "c3a1e0b5-1c88-4903-8d2e-3362174dfb67",
    "organization_name": "Hope Community Kitchen",
    "capacity_daily_kg": 500.0,
    "cold_storage_capabilities": {
      "refrigeration": true,
      "freezer": true
    },
    "priority_level": 4
  }
  ```

---

### 2.4 Surplus Listings (`/surplus`)

#### `POST /api/v1/surplus/`
* **Purpose:** Post a new batch of perishable surplus food.
* **Auth:** Supplier.
* **Request Body:**
  ```json
  {
    "food_category": "DAIRY",
    "item_name": "Pasteurized Whole Milk (1L Cartons)",
    "initial_quantity_kg": 150.0,
    "storage_condition": "REFRIGERATED",
    "food_condition": "EXCELLENT",
    "harvest_or_prep_date": "2026-10-31T06:00:00Z",
    "estimated_deadline": "2026-11-01T12:00:00Z"
  }
  ```
* **Success Response (`201 Created`):**
  ```json
  {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "item_name": "Pasteurized Whole Milk (1L Cartons)",
    "remaining_quantity_kg": 150.0,
    "urgency_classification": "CRITICAL",
    "remaining_usable_hours": 5.5,
    "status": "AVAILABLE"
  }
  ```
* **Errors:** `422 Unprocessable Entity` (Deadline in the past, non-positive quantity).

---

#### `GET /api/v1/surplus/`
* **Purpose:** Search and list active surplus inventory with filtering.
* **Auth:** Authenticated.
* **Query Parameters:** `status`, `food_category`, `urgency`, `limit`, `offset`.
* **Success Response (`200 OK`):**
  ```json
  {
    "total": 1,
    "items": [
      {
        "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "supplier_name": "Metro Fresh Supermarket",
        "food_category": "DAIRY",
        "item_name": "Pasteurized Whole Milk (1L Cartons)",
        "remaining_quantity_kg": 150.0,
        "urgency_classification": "CRITICAL",
        "estimated_deadline": "2026-11-01T12:00:00Z",
        "status": "AVAILABLE"
      }
    ]
  }
  ```

---

### 2.5 Demand Requests (`/demand`)

#### `POST /api/v1/demand/`
* **Purpose:** Create a food intake request for a recipient organization.
* **Auth:** Receiver.
* **Request Body:**
  ```json
  {
    "food_category": "DAIRY",
    "requested_quantity_kg": 100.0,
    "dietary_requirements": ["VEGETARIAN"],
    "storage_capability": "REFRIGERATED",
    "required_by": "2026-11-01T14:00:00Z",
    "priority_weight": 4
  }
  ```
* **Success Response (`201 Created`):**
  ```json
  {
    "id": "7b88e1a2-63b1-4f11-9a73-8a39527cfdb2",
    "requested_quantity_kg": 100.0,
    "fulfilled_quantity_kg": 0.0,
    "status": "ACTIVE"
  }
  ```

---

### 2.6 Matching & Allocation Proposals (`/matching` & `/proposals`)

#### `POST /api/v1/matching/candidates`
* **Purpose:** Evaluate compatibility matrix between active surplus and active demand without committing.
* **Auth:** Coordinator or Admin.
* **Request Body:**
  ```json
  {
    "max_distance_km": 30.0,
    "filter_category": "DAIRY"
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
    "feasible_pairs_count": 4,
    "pairs": [
      {
        "surplus_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "demand_id": "7b88e1a2-63b1-4f11-9a73-8a39527cfdb2",
        "distance_km": 4.8,
        "estimated_transit_minutes": 14,
        "dietary_compatible": true,
        "storage_compatible": true
      }
    ]
  }
  ```

---

#### `POST /api/v1/proposals/generate`
* **Purpose:** Trigger Google OR-Tools optimization and AI Agent synthesis to produce a formal redistribution proposal.
* **Auth:** Coordinator or Admin.
* **Request Body:**
  ```json
  {
    "urgency_weight": 1.5,
    "distance_penalty_weight": 0.5,
    "priority_weight": 1.2
  }
  ```
* **Success Response (`201 Created`):**
  ```json
  {
    "proposal_id": "e9b25712-4c60-4963-8a4a-10f842d06b3a",
    "status": "PENDING_REVIEW",
    "total_allocated_kg": 100.0,
    "total_unallocated_kg": 50.0,
    "total_unmet_demand_kg": 0.0,
    "estimated_total_transit_km": 4.8,
    "ai_justification": "Allocated 100 kg of dairy from Metro Fresh to Hope Community Kitchen. Metro Fresh milk deadline is in 5.5 hours; Hope Community has confirmed refrigeration and is located 4.8 km (14 mins) away.",
    "items": [
      {
        "surplus_listing_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "demand_request_id": "7b88e1a2-63b1-4f11-9a73-8a39527cfdb2",
        "allocated_quantity_kg": 100.0,
        "distance_km": 4.8,
        "transit_minutes": 14
      }
    ]
  }
  ```

---

#### `POST /api/v1/optimization/proposals/{id}/approve`
* **Purpose:** Coordinator or Admin approval that commits an allocation proposal, executes atomic row-level locks, decrements inventory, and issues a traceable `RedistributionTransaction`.
* **Auth:** Coordinator or Admin only (LLMs forbidden).
* **Request Body (Optional):**
  ```json
  {
    "dispatch_notes": "Loading dock 3, driver requires insulated crates.",
    "scheduled_pickup_at": "2026-11-01T15:30:00Z"
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
    "id": "3f8295b7-7201-4993-9c59-bfbc781c0378",
    "proposal_id": "e9b25712-4c60-4963-8a4a-10f842d06b3a",
    "tracking_code": "FHD-TX-20261101-9C59",
    "status": "APPROVED",
    "scheduled_pickup_at": "2026-11-01T15:30:00Z",
    "dispatch_notes": "Loading dock 3, driver requires insulated crates.",
    "total_allocated_kg": 100.0,
    "items_count": 1,
    "items": [
      {
        "item_id": "8c420e11-8210-4822-b9e3-8209bb42a001",
        "surplus_listing_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "demand_request_id": "7b88e1a2-63b1-4f11-9a73-8a39527cfdb2",
        "supplier_id": "2b31a89c-4819-4841-ba66-993d073d8421",
        "receiver_id": "1c984210-91b4-4284-88f1-443b7194821a",
        "supplier_name": "Metro Fresh Distribution",
        "receiver_name": "Hope Community Kitchen",
        "item_name": "Organic Whole Milk",
        "food_category": "DAIRY",
        "allocated_quantity_kg": 100.0,
        "estimated_distance_km": 4.8,
        "estimated_transit_minutes": 14,
        "urgency_at_allocation": "HIGH"
      }
    ],
    "status_history": [
      {
        "id": "12345678-1234-5678-1234-567812345678",
        "previous_status": null,
        "new_status": "APPROVED",
        "changed_by_user_id": "99887766-5544-3322-1100-aabbccddeeff",
        "reason": "Human coordinator approval",
        "changed_at": "2026-11-01T12:00:00Z"
      }
    ],
    "created_at": "2026-11-01T12:00:00Z",
    "updated_at": "2026-11-01T12:00:00Z"
  }
  ```
* **Errors:**
  * `400 Bad Request`: Invalid transition (proposal not in `PENDING_REVIEW`).
  * `403 Forbidden`: Unauthorized user role (Supplier/Receiver/AI).
  * `404 Not Found`: Proposal ID not found.
  * `409 Conflict`: Pre-execution revalidation failed (perishability deadline elapsed, insufficient inventory remaining, demand closed).

---

#### `POST /api/v1/optimization/proposals/{id}/reject`
* **Purpose:** Coordinator or Admin rejection of an allocation proposal with mandatory justification.
* **Auth:** Coordinator or Admin only.
* **Request Body:**
  ```json
  {
    "reason": "Receiver cold storage compressor failed this morning; cannot accept dairy."
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
    "proposal_id": "e9b25712-4c60-4963-8a4a-10f842d06b3a",
    "status": "REJECTED",
    "message": "Proposal rejected successfully.",
    "rejection_reason": "Receiver cold storage compressor failed this morning; cannot accept dairy."
  }
  ```

---

### 2.7 Redistribution Transactions (`/transactions`)

#### `GET /api/v1/transactions`
* **Purpose:** List all redistribution transactions with optional status filter.
* **Auth:** Coordinator or Admin.
* **Query Parameters:** `status` (optional), `limit` (default 50), `offset` (default 0).
* **Success Response (`200 OK`):**
  ```json
  {
    "total_count": 1,
    "items": [ /* List of TransactionResponse */ ]
  }
  ```

#### `GET /api/v1/transactions/{id}`
* **Purpose:** Retrieve live tracking, state history, and line items for a transaction.
* **Auth:** Coordinator, Admin, or participating Supplier/Receiver.
* **Success Response (`200 OK`):** Full `TransactionResponse` object.

#### `POST /api/v1/transactions/{id}/execute`
* **Purpose:** Advance an `APPROVED` transaction to `PICKUP_SCHEDULED`, setting associated proposal status to `EXECUTING`.
* **Auth:** Coordinator or Admin.
* **Success Response (`200 OK`):** Full `TransactionResponse` with updated status and appended history log.

#### `PATCH /api/v1/transactions/{id}/status`
* **Purpose:** Advance a transaction along its custody checkpoints (`PICKUP_SCHEDULED`, `PICKED_UP`, `IN_TRANSIT`, `DELIVERED`, `COMPLETED`, `FAILED`, `CANCELLED`).
* **Auth:** Coordinator or Admin.
* **Request Body:**
  ```json
  {
    "status": "IN_TRANSIT",
    "reason": "Driver dispatched from depot.",
    "actual_pickup_at": "2026-11-01T14:15:00Z",
    "dispatch_notes": "Departed via Highway 101."
  }
  ```
* **Success Response (`200 OK`):** Full updated `TransactionResponse`.
* **Rollback Note:** If transitioned to `CANCELLED`, all remaining quantities are restored to active surplus listings and decremented from demand fulfillment.

---

### 2.8 What-If Simulations (`/simulations`)

#### `POST /api/v1/simulations/run`
* **Purpose:** Execute an isolated disruption simulation against current in-memory inventory without mutating database state.
* **Auth:** Coordinator or Admin.
* **Request Body:**
  ```json
  {
    "scenario_type": "RECEIVER_UNAVAILABLE",
    "disruption_parameters": {
      "blocked_receiver_id": "c3a1e0b5-1c88-4903-8d2e-3362174dfb67"
    }
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
    "simulation_id": "78201a09-7d12-4299-8801-ecbbfa5d8201",
    "scenario_type": "RECEIVER_UNAVAILABLE",
    "baseline": {
      "salvaged_kg": 450.0,
      "unallocated_kg": 50.0
    },
    "simulated": {
      "salvaged_kg": 350.0,
      "unallocated_kg": 150.0
    },
    "impact_delta": {
      "lost_salvage_kg": 100.0,
      "unfulfilled_demand_delta_kg": 100.0
    },
    "recommendation": "Deploy mobile refrigeration truck to temporarily stage the 100 kg batch, or redirect to Westside Pantry (12 km)."
  }
  ```

---

### 2.9 Analytics & Impact (`/analytics`)

#### `GET /api/v1/analytics/overview`
* **Purpose:** Retrieve system-wide sustainability and redistribution KPIs.
* **Auth:** Authenticated.
* **Success Response (`200 OK`):**
  ```json
  {
    "total_food_salvaged_kg": 12450.0,
    "co2_emissions_avoided_kg": 31125.0,
    "meals_equivalent_provided": 24900,
    "average_urgency_resolution_hours": 3.8,
    "active_suppliers_count": 28,
    "active_receivers_count": 42
  }
  ```

---

### 2.10 Monitoring & Health Checks

#### `GET /health`
* **Purpose:** Service health and operational dependency check.
* **Auth:** Public.
* **Success Response (`200 OK`):**
  ```json
  {
    "status": "healthy",
    "app_name": "Food Has a Deadline",
    "version": "0.1.0",
    "environment": "development",
    "ai_configured": true,
    "database": {
      "status": "connected",
      "connected": true,
      "details": "PostgreSQL database connection verified"
    }
  }
  ```

---

### 2.11 Geospatial Intelligence & Routing (`/geospatial`, `/receivers`)

#### `POST /api/v1/geospatial/route-estimate`
* **Purpose:** Compute great-circle Haversine distance, road distance, transit duration, and temporal shelf-life feasibility between a registered surplus food listing and a receiver destination. Coordinates are strictly retrieved from PostgreSQL facility profiles.
* **Auth:** Bearer JWT (`SUPPLIER` owning the listing, `RECEIVER` owning the profile, or `COORDINATOR` / `ADMIN`).
* **Request Body:**
  ```json
  {
    "surplus_listing_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "receiver_id": "7ca64b22-8114-4c8d-b3ef-8a3b5a1b3299",
    "handling_buffer_minutes": 30
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
    "supplier_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "receiver_id": "7ca64b22-8114-4c8d-b3ef-8a3b5a1b3299",
    "supplier_name": "San Francisco Central Farm",
    "receiver_name": "Oakland Community Food Bank",
    "supplier_coordinates": {
      "latitude": 37.7955,
      "longitude": -122.3937
    },
    "receiver_coordinates": {
      "latitude": 37.8044,
      "longitude": -122.2711
    },
    "straight_line_distance_km": 10.82,
    "road_distance_km": 15.42,
    "estimated_travel_minutes": 23.0,
    "routing_provider": "OSRM",
    "is_fallback": false,
    "route_geometry": {
      "type": "LineString",
      "coordinates": [
        [-122.3937, 37.7955],
        [-122.2711, 37.8044]
      ]
    },
    "feasibility": "FEASIBLE",
    "available_minutes": 240.0,
    "required_minutes": 53.0,
    "handling_buffer_minutes": 30,
    "warnings": [],
    "evaluated_at": "2026-10-31T15:00:00Z"
  }
  ```
* **Fallback Behavior:** When external OSRM is unreachable or times out (3.0s), returns `routing_provider: "HAVERSINE_FALLBACK"`, `is_fallback: true`, `route_geometry: null`, approximated road distance ($1.35 \times \text{straight-line}$), and travel duration ($35 \text{ km/h}$). Zero fabricated geometries.
* **Errors:** `400 Bad Request` (Missing coordinates in profiles), `401 Unauthorized`, `403 Forbidden` (Role permissions), `404 Not Found` (Listing or Receiver not found or cross-tenant ownership violation).

---

#### `GET /api/v1/receivers/directory`
* **Purpose:** Retrieve list of registered receiver organizations with facility coordinates and capacities for destination selection.
* **Auth:** Bearer JWT (Any authenticated user).
* **Success Response (`200 OK`):**
  ```json
  [
    {
      "id": "7ca64b22-8114-4c8d-b3ef-8a3b5a1b3299",
      "user_id": "4e1a074c-8bb2-4fa0-82a9-7fa1e52db9a2",
      "organization_name": "Oakland Community Food Bank",
      "contact_phone": "+1-555-2222",
      "address": "123 City Center",
      "state": "California",
      "district": "Alameda",
      "city": "Oakland",
      "latitude": 37.8044,
      "longitude": -122.2711,
      "receiver_category": "FOOD_BANK",
      "capacity_daily_kg": 500.0,
      "priority_level": 4,
      "cold_storage_capabilities": {
        "refrigeration": true,
        "freezer": false
      },
      "created_at": "2026-10-31T12:00:00Z",
      "updated_at": "2026-10-31T12:00:00Z"
    }
  ]
  ```

---

### 2.12 Supply-Demand Matching Engine (`/matching`)

#### `GET /api/v1/matching/listings/{listing_id}/candidates`
* **Purpose:** Retrieve ranked, compatible receiver demand candidates for a surplus food listing. Evaluates product category, dietary requirements, condition thresholds, cold chain storage capabilities, and road transit feasibility. Strictly read-only.
* **Auth:** Bearer JWT (`SUPPLIER` owning the listing, or `COORDINATOR` / `ADMIN`).
* **Query Parameters:**
  * `page` (int, default: 1)
  * `page_size` (int, default: 20, max: 100)
  * `include_ineligible` (bool, default: false)
* **Success Response (`200 OK`):**
  ```json
  {
    "source_type": "SURPLUS_LISTING",
    "source_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "source_name": "Crisp Apples",
    "total_candidates": 3,
    "eligible_count": 2,
    "ineligible_count": 1,
    "review_required_count": 0,
    "page": 1,
    "page_size": 20,
    "candidates": [
      {
        "candidate_id": "c7a8b9c0-1234-5678-9abc-def012345678",
        "surplus_listing_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "demand_request_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
        "supplier_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "receiver_id": "7ca64b22-8114-4c8d-b3ef-8a3b5a1b3299",
        "supplier_name": "Valley Orchard Co.",
        "receiver_name": "Santa Rosa Community Kitchen",
        "item_name": "Fresh Apples",
        "food_category": "FRUITS",
        "eligibility": "ELIGIBLE",
        "is_eligible": true,
        "rejection_reasons": [],
        "product_compatibility": {
          "match_level": "SUBSET_COMPATIBLE",
          "is_compatible": true,
          "category_match": true,
          "item_match": true,
          "dietary_compatible": true,
          "condition_compatible": true,
          "dietary_flags": [],
          "warnings": [],
          "notes": "Direct category match: 'FRUITS'; Core commodity match on apples."
        },
        "quantity_compatibility": {
          "match_level": "FULL_SATISFACTION",
          "is_compatible": true,
          "surplus_available_kg": 100.0,
          "demand_outstanding_kg": 60.0,
          "matched_quantity_kg": 60.0,
          "fulfillment_ratio": 1.0,
          "surplus_utilization_ratio": 0.6,
          "is_partial": false,
          "notes": "Surplus batch (100.0 kg) can completely fulfill the outstanding receiver requirement (60.0 kg)."
        },
        "storage_compatibility": {
          "match_level": "COMPATIBLE",
          "is_compatible": true,
          "required_storage": "AMBIENT",
          "available_storage": "AMBIENT",
          "receiver_has_cold_chain": false,
          "warnings": [],
          "notes": "Ambient surplus requires standard non-chilled storage, supported by all facilities."
        },
        "perishability_urgency": "HIGH",
        "remaining_shelf_life_hours": 20.0,
        "transit_feasibility": "FEASIBLE",
        "straight_line_distance_km": 8.5,
        "road_distance_km": 11.47,
        "estimated_transit_minutes": 19.7,
        "handling_buffer_minutes": 30,
        "routing_provider": "OSRM",
        "is_route_fallback": false,
        "receiver_priority": 4,
        "receiver_category": "COMMUNITY_KITCHEN",
        "score": 82.4,
        "score_breakdown": {
          "urgency_score": 80.0,
          "proximity_score": 63.2,
          "shelf_life_margin_score": 100.0,
          "quantity_fit_score": 100.0,
          "priority_score": 85.0,
          "total_score": 82.4
        },
        "warnings": [],
        "explanation": "ELIGIBLE candidate (Score: 82.4/100): Product and storage compatible. Logistics feasible via OSRM driving route (11.47 km, ~19.7 mins transit). Surplus fully fulfills 60.0 kg requested with 20.0 hrs of usable shelf life remaining (HIGH urgency).",
        "evaluated_at": "2026-10-31T22:30:00Z"
      }
    ]
  }
  ```
* **Errors:** `401 Unauthorized`, `403 Forbidden`, `404 Not Found`.

---

#### `GET /api/v1/matching/demands/{demand_id}/candidates`
* **Purpose:** Retrieve ranked, compatible surplus inventory listings capable of fulfilling a registered receiver demand request. Strictly read-only.
* **Auth:** Bearer JWT (`RECEIVER` owning the demand, or `COORDINATOR` / `ADMIN`).
* **Query Parameters:** `page`, `page_size`, `include_ineligible`.
* **Success Response (`200 OK`):** Symmetrical schema to `/listings/{listing_id}/candidates` with `source_type: "DEMAND_REQUEST"`.

---

### 7. Google OR-Tools Allocation Optimization Subsystem (Module 8)

#### `POST /api/v1/optimization/allocation-proposals`
* **Purpose:** Formulate and solve the multi-commodity capacitated redistribution optimization problem using Google OR-Tools CP-SAT. Generates an optimal redistribution proposal without executing transfers or mutating inventory.
* **Auth:** Bearer JWT (Restricted to `COORDINATOR` and `ADMIN` roles).
* **Request Body:**
  ```json
  {
    "surplus_listing_ids": ["uuid-optional"],
    "demand_request_ids": ["uuid-optional"],
    "timeout_seconds": 5.0,
    "max_distance_km": 50.0,
    "evaluation_time": "2026-10-31T22:30:00Z"
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
    "proposal_id": "4b684cb3-0dc2-4ee4-904c-3e617f1680d2",
    "status": "PENDING_REVIEW",
    "total_allocated_kg": 80.0,
    "total_unallocated_kg": 20.0,
    "total_unmet_demand_kg": 0.0,
    "estimated_total_transit_km": 11.47,
    "solver_status": "OPTIMAL",
    "solve_time_ms": 14.2,
    "ai_justification": "Google OR-Tools CP-SAT (OPTIMAL) successfully proposed redistribution of 80.00 kg across 1 allocation flow connecting 1 supplier facility to 1 receiver organization...",
    "items": [
      {
        "item_id": "5a76c8c9-8d63-4bf5-88e2-b13c013bcda1",
        "proposal_id": "4b684cb3-0dc2-4ee4-904c-3e617f1680d2",
        "surplus_listing_id": "8bb3858a-360e-43f6-be11-8ecb7ad4f7cb",
        "demand_request_id": "31b01476-c567-4632-a567-5fb5fbc2a5fe",
        "supplier_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
        "receiver_id": "f1e2d3c4-b5a6-7890-1234-56789abcdef0",
        "supplier_name": "Valley Orchard Co.",
        "receiver_name": "Santa Rosa Community Kitchen",
        "item_name": "Organic Honeycrisp Apples",
        "food_category": "FRUITS",
        "allocated_quantity_kg": 80.0,
        "estimated_distance_km": 11.47,
        "estimated_transit_minutes": 20,
        "urgency_at_allocation": "HIGH",
        "shelf_life_slack_minutes": 1150.0,
        "allocation_score": 85.0,
        "explanation": "Allocated 80.00 kg to Santa Rosa Community Kitchen (Priority 4) via 11.5 km road route."
      }
    ],
    "unfulfilled_demands": [],
    "unallocated_surplus": [
      {
        "surplus_listing_id": "8bb3858a-360e-43f6-be11-8ecb7ad4f7cb",
        "supplier_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
        "supplier_name": "Valley Orchard Co.",
        "food_category": "FRUITS",
        "item_name": "Organic Honeycrisp Apples",
        "available_quantity_kg": 100.0,
        "allocated_in_proposal_kg": 80.0,
        "unallocated_quantity_kg": 20.0,
        "urgency": "HIGH",
        "reason_code": "ALL_DEMANDS_FULFILLED",
        "diagnostic_explanation": "Compatible local receiver demands were already satisfied or reached capacity limits."
      }
    ],
    "diagnostics": {
      "solver_name": "Google OR-Tools CP-SAT",
      "solver_status": "OPTIMAL",
      "solve_time_ms": 14.2,
      "num_surplus_considered": 1,
      "num_demands_considered": 1,
      "num_candidate_pairs": 1,
      "num_variables": 1,
      "num_constraints": 2,
      "objective_value": 117200.0
    },
    "created_at": "2026-10-31T22:35:00Z"
  }
  ```
* **Errors:** `401 Unauthorized`, `403 Forbidden` (non-coordinators), `422 Unprocessable Content`.

---

#### `GET /api/v1/optimization/proposals/{proposal_id}`
* **Purpose:** Retrieve a previously persisted allocation proposal with full line item details and solver metadata.
* **Auth:** Bearer JWT (Restricted to `COORDINATOR` and `ADMIN` roles).
* **Success Response (`200 OK`):** Symmetrical schema to `OptimizationProposalResponse`.
* **Errors:** `401 Unauthorized`, `403 Forbidden`, `404 Not Found`.

---

### 2.9 AI Redistribution Agent Endpoints (`/agent`)

#### `POST /api/v1/agent/chat`
* **Purpose:** Submits a natural language message to the AI Redistribution Agent. Enforces role-based function declarations, prompt injection defense, multi-turn tool execution across deterministic backend modules, and resilient fallback generation.
* **Auth:** Bearer JWT (All authenticated roles: `SUPPLIER`, `RECEIVER`, `COORDINATOR`, `ADMIN`).
* **Request Body:**
  ```json
  {
    "message": "What surplus food is available right now?",
    "conversation_id": "optional-uuid"
  }
  ```
* **Success Response (`200 OK`):**
  ```json
  {
    "conversation_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
    "message_id": "m1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
    "response_text": "I checked the network inventory. There are 2 active surplus batches available...",
    "tool_calls": [
      {
        "call_id": "call_12345678",
        "tool_name": "get_available_surplus",
        "arguments": { "limit": 10 }
      }
    ],
    "tool_results": [
      {
        "call_id": "call_12345678",
        "tool_name": "get_available_surplus",
        "output": { "total_found": 2, "listings": [] },
        "success": true,
        "error": null
      }
    ],
    "proposal_preview": null,
    "ai_provider": "Google Gemini",
    "fallback_mode": false,
    "created_at": "2026-11-01T06:00:00Z"
  }
  ```
* **Errors:** `401 Unauthorized`, `422 Unprocessable Content`.

---

#### `GET /api/v1/agent/conversations`
* **Purpose:** List recent conversation threads belonging to the authenticated user.
* **Auth:** Bearer JWT.
* **Query Parameters:** `limit` (default: 50, max: 100).
* **Success Response (`200 OK`):**
  ```json
  [
    {
      "id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
      "title": "What surplus food is available right now?",
      "message_count": 4,
      "created_at": "2026-11-01T05:50:00Z",
      "updated_at": "2026-11-01T06:00:00Z"
    }
  ]
  ```
* **Errors:** `401 Unauthorized`.

---

#### `GET /api/v1/agent/conversations/{conversation_id}`
* **Purpose:** Retrieve full chronological message history, tool calls, and tool results for a specific conversation.
* **Auth:** Bearer JWT (Multi-tenant isolated; only the owning user can access).
* **Success Response (`200 OK`):**
  ```json
  {
    "id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
    "title": "Redistribution Session",
    "messages": [
      {
        "id": "m1a2b3c4-...",
        "role": "user",
        "content": "Check active surplus.",
        "tool_calls": null,
        "tool_results": null,
        "proposal_id": null,
        "created_at": "2026-11-01T05:50:00Z"
      },
      {
        "id": "m2a2b3c4-...",
        "role": "assistant",
        "content": "Found 2 active batches.",
        "tool_calls": [],
        "tool_results": [],
        "proposal_id": null,
        "created_at": "2026-11-01T05:50:02Z"
      }
    ],
    "created_at": "2026-11-01T05:50:00Z",
    "updated_at": "2026-11-01T05:50:02Z"
  }
  ```
* **Errors:** `401 Unauthorized`, `404 Not Found`.

---

#### `DELETE /api/v1/agent/conversations/{conversation_id}`
* **Purpose:** Permanently delete a conversation thread and its messages.
* **Auth:** Bearer JWT (Owner only).
* **Success Response (`200 OK`):**
  ```json
  {
    "deleted": true,
    "conversation_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c"
  }
  ```
* **Errors:** `401 Unauthorized`, `404 Not Found`.

---

#### `GET /api/v1/agent/tools`
* **Purpose:** Return the list of authorized tool declarations and parameter schemas for the authenticated user's role.
* **Auth:** Bearer JWT.
* **Success Response (`200 OK`):**
  ```json
  [
    {
      "name": "get_available_surplus",
      "description": "Queries active supplier surplus food batches...",
      "parameters": {
        "type": "OBJECT",
        "properties": {}
      }
    }
  ]
  ```
* **Errors:** `401 Unauthorized`.


