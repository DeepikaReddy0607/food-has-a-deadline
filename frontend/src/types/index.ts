export type UserRole = 'SUPPLIER' | 'RECEIVER' | 'COORDINATOR' | 'ADMIN'

export interface UserSummary {
  id: string
  email: string
  role: UserRole
}

export interface UserPublic {
  id: string
  email: string
  role: UserRole
  is_active: boolean
  is_verified: boolean
  created_at: string
  profile?: Record<string, unknown> | null
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in_minutes: number
  user: UserSummary
}

export interface HealthResponse {
  status: string
  app_name: string
  version: string
  environment: string
  database: {
    status: string
    connected: boolean
    details?: string
  }
}

export interface AppInfoResponse {
  name: string
  tagline: string
  version: string
  docs_url: string
}

export type FacilityType =
  | 'FARM'
  | 'WHOLESALER'
  | 'RETAILER'
  | 'RESTAURANT'
  | 'FOOD_PROCESSOR'
  | 'OTHER'

export interface SupplierStorageCapabilities {
  ambient: boolean
  refrigerated: boolean
  frozen: boolean
}

export interface SupplierProfile {
  id: string
  user_id: string
  organization_name: string
  contact_phone: string
  address: string
  state?: string | null
  district?: string | null
  city?: string | null
  latitude: number
  longitude: number
  facility_type: FacilityType
  operating_hours?: Record<string, unknown> | null
  storage_capabilities?: SupplierStorageCapabilities | null
  description?: string | null
  created_at: string
  updated_at: string
}

export interface SupplierProfileCreatePayload {
  organization_name: string
  contact_phone: string
  address: string
  state?: string
  district?: string
  city?: string
  latitude: number
  longitude: number
  facility_type: FacilityType
  operating_hours?: Record<string, unknown>
  storage_capabilities?: SupplierStorageCapabilities
  description?: string
}

export interface SupplierProfileUpdatePayload {
  organization_name?: string
  contact_phone?: string
  address?: string
  state?: string
  district?: string
  city?: string
  latitude?: number
  longitude?: number
  facility_type?: FacilityType
  operating_hours?: Record<string, unknown>
  storage_capabilities?: SupplierStorageCapabilities
  description?: string
}

export type ReceiverCategory =
  | 'FOOD_BANK'
  | 'NGO'
  | 'COMMUNITY_KITCHEN'
  | 'SHELTER'
  | 'HOSPITAL'
  | 'OTHER'

export interface ReceiverColdStorageCapabilities {
  refrigeration: boolean
  freezer: boolean
}

export interface ReceiverProfile {
  id: string
  user_id: string
  organization_name: string
  contact_phone: string
  address: string
  state?: string | null
  district?: string | null
  city?: string | null
  latitude: number
  longitude: number
  receiver_category?: ReceiverCategory | null
  capacity_daily_kg: number
  cold_storage_capabilities?: ReceiverColdStorageCapabilities | null
  dietary_handling_capabilities?: string[] | null
  operating_hours?: Record<string, unknown> | null
  priority_level: number
  description?: string | null
  created_at: string
  updated_at: string
}

export interface ReceiverProfileCreatePayload {
  organization_name: string
  contact_phone: string
  address: string
  state?: string
  district?: string
  city?: string
  latitude: number
  longitude: number
  receiver_category: ReceiverCategory
  capacity_daily_kg: number
  cold_storage_capabilities?: ReceiverColdStorageCapabilities
  dietary_handling_capabilities?: string[]
  operating_hours?: Record<string, unknown>
  priority_level: number
  description?: string
}

export interface ReceiverProfileUpdatePayload {
  organization_name?: string
  contact_phone?: string
  address?: string
  state?: string
  district?: string
  city?: string
  latitude?: number
  longitude?: number
  receiver_category?: ReceiverCategory
  capacity_daily_kg?: number
  cold_storage_capabilities?: ReceiverColdStorageCapabilities
  dietary_handling_capabilities?: string[]
  operating_hours?: Record<string, unknown>
  priority_level?: number
  description?: string
}

// =========================================================================
// MODULE 4: SURPLUS INVENTORY TYPES
// =========================================================================

export type FoodCategory =
  | 'FRUITS'
  | 'VEGETABLES'
  | 'GRAINS'
  | 'DAIRY'
  | 'BAKERY'
  | 'COOKED_FOOD'
  | 'OTHER'

export type FoodCondition =
  | 'EXCELLENT'
  | 'GOOD'
  | 'FAIR'
  | 'RIPE'
  | 'IMMINENT_DECAY'
  | 'IMPERFECT'

export type StorageCondition = 'AMBIENT' | 'REFRIGERATED' | 'FROZEN'

export type SurplusStatus =
  | 'ACTIVE'
  | 'PAUSED'
  | 'DEPLETED'
  | 'EXPIRED'
  | 'CANCELLED'

export type UrgencyClassification =
  | 'CRITICAL'
  | 'HIGH'
  | 'MODERATE'
  | 'LOW'
  | 'PENDING'

export interface SurplusListing {
  id: string
  supplier_id: string
  food_category: FoodCategory
  item_name: string
  description?: string | null
  initial_quantity_kg: number
  remaining_quantity_kg: number
  storage_condition: StorageCondition
  food_condition: FoodCondition
  harvest_or_prep_date: string
  preparation_date?: string | null
  estimated_deadline: string
  pickup_address?: string | null
  handling_instructions?: string | null
  urgency_classification: UrgencyClassification
  status: SurplusStatus
  created_at: string
  updated_at: string
}

export interface SurplusListingCreatePayload {
  food_category: string
  item_name: string
  description?: string
  initial_quantity_kg: number
  harvest_or_prep_date: string
  preparation_date?: string
  estimated_deadline: string
  food_condition?: string
  storage_condition?: string
  pickup_address?: string
  handling_instructions?: string
}

export interface SurplusListingUpdatePayload {
  item_name?: string
  description?: string
  remaining_quantity_kg?: number
  estimated_deadline?: string
  food_condition?: string
  storage_condition?: string
  pickup_address?: string
  handling_instructions?: string
}

export interface SurplusPaginationResponse {
  items: SurplusListing[]
  total: number
  page: number
  page_size: number
  pages: number
}

// =========================================================================
// MODULE 4: DEMAND MANAGEMENT TYPES
// =========================================================================

export type DemandStatus =
  | 'OPEN'
  | 'PAUSED'
  | 'PARTIALLY_FULFILLED'
  | 'FULFILLED'
  | 'EXPIRED'
  | 'CANCELLED'

export interface DemandRequest {
  id: string
  receiver_id: string
  food_category: string
  item_name?: string | null
  description?: string | null
  requested_quantity_kg: number
  fulfilled_quantity_kg: number
  remaining_requirement_kg: number
  acceptable_food_condition?: string | null
  dietary_requirements: string[]
  storage_capability: string
  delivery_address?: string | null
  handling_instructions?: string | null
  priority_weight: number
  status: DemandStatus
  required_by: string
  created_at: string
  updated_at: string
}

export interface DemandRequestCreatePayload {
  food_category: string
  item_name?: string
  description?: string
  requested_quantity_kg: number
  required_by: string
  acceptable_food_condition?: string
  dietary_requirements?: string[]
  storage_capability?: string
  delivery_address?: string
  handling_instructions?: string
  priority_weight?: number
}

export interface DemandRequestUpdatePayload {
  item_name?: string
  description?: string
  requested_quantity_kg?: number
  required_by?: string
  acceptable_food_condition?: string
  dietary_requirements?: string[]
  storage_capability?: string
  delivery_address?: string
  handling_instructions?: string
  priority_weight?: number
}

export interface DemandPaginationResponse {
  items: DemandRequest[]
  total: number
  page: number
  page_size: number
  pages: number
}

// =========================================================================
// MODULE 5: DETERMINISTIC PERISHABILITY INTELLIGENCE TYPES
// =========================================================================

export type DataQualityLevel = 'COMPLETE' | 'PARTIAL' | 'SUSPECT' | 'INVALID'

export interface PerishabilityEvaluation {
  listing_id?: string | null
  remaining_seconds: number
  remaining_hours: number
  urgency: UrgencyClassification
  condition: string
  storage_condition: string
  warnings: string[]
  explanation: string
  data_quality: DataQualityLevel
  evaluated_at: string
  factors: Record<string, unknown>
  disclaimer: string
}

export interface BatchEvaluationResponse {
  total_evaluated: number
  counts_by_urgency: Record<string, number>
  items: PerishabilityEvaluation[]
}

// =========================================================================
// MODULE 6: GEOSPATIAL INTELLIGENCE AND ROUTING TYPES
// =========================================================================

export type FeasibilityStatus = 'FEASIBLE' | 'INFEASIBLE' | 'UNKNOWN'
export type RoutingProvider = 'OSRM' | 'HAVERSINE_FALLBACK'

export interface Coordinates {
  latitude: number
  longitude: number
}

export interface RouteGeometry {
  type: string
  coordinates: [number, number][]
}

export interface RouteEstimateRequest {
  receiver_id: string
  surplus_listing_id: string
  handling_buffer_minutes?: number
}

export interface RouteEstimateResult {
  supplier_id: string
  receiver_id: string
  supplier_name?: string | null
  receiver_name?: string | null
  supplier_coordinates: Coordinates
  receiver_coordinates: Coordinates
  straight_line_distance_km: number
  road_distance_km: number
  estimated_travel_minutes: number
  routing_provider: RoutingProvider
  is_fallback: boolean
  route_geometry?: RouteGeometry | null
  feasibility: FeasibilityStatus
  available_minutes?: number | null
  required_minutes?: number | null
  handling_buffer_minutes: number
  warnings: string[]
  evaluated_at: string
}

// =========================================================================
// MODULE 7: MULTI-FACTOR SUPPLY-DEMAND MATCHING TYPES
// =========================================================================

export type EligibilityStatus = 'ELIGIBLE' | 'INELIGIBLE' | 'REVIEW_REQUIRED'
export type ProductMatchLevel = 'EXACT' | 'CATEGORY_COMPATIBLE' | 'SUBSET_COMPATIBLE' | 'INCOMPATIBLE' | 'AMBIGUOUS'
export type StorageMatchLevel = 'COMPATIBLE' | 'INCOMPATIBLE' | 'UNKNOWN'
export type QuantityMatchLevel = 'FULL_SATISFACTION' | 'PARTIAL_SATISFACTION' | 'ZERO_SURPLUS' | 'ZERO_DEMAND'

export interface ProductCompatibilityResult {
  match_level: ProductMatchLevel
  is_compatible: boolean
  category_match: boolean
  item_match?: boolean | null
  dietary_compatible: boolean
  condition_compatible: boolean
  dietary_flags: string[]
  warnings: string[]
  notes: string
}

export interface StorageCompatibilityResult {
  match_level: StorageMatchLevel
  is_compatible: boolean
  required_storage: string
  available_storage: string
  receiver_has_cold_chain: boolean
  warnings: string[]
  notes: string
}

export interface QuantityCompatibilityResult {
  match_level: QuantityMatchLevel
  is_compatible: boolean
  surplus_available_kg: number
  demand_outstanding_kg: number
  matched_quantity_kg: number
  fulfillment_ratio: number
  surplus_utilization_ratio: number
  is_partial: boolean
  notes: string
}

export interface ScoreBreakdown {
  urgency_score: number
  proximity_score: number
  shelf_life_margin_score: number
  quantity_fit_score: number
  priority_score: number
  total_score: number
}

export interface CandidateMatch {
  candidate_id: string
  surplus_listing_id: string
  demand_request_id: string
  supplier_id: string
  receiver_id: string
  supplier_name: string
  receiver_name: string
  item_name: string
  food_category: string
  eligibility: EligibilityStatus
  is_eligible: boolean
  rejection_reasons: string[]
  product_compatibility: ProductCompatibilityResult
  quantity_compatibility: QuantityCompatibilityResult
  storage_compatibility: StorageCompatibilityResult
  perishability_urgency: string
  remaining_shelf_life_hours: number
  transit_feasibility: string
  straight_line_distance_km: number
  road_distance_km: number
  estimated_transit_minutes: number
  handling_buffer_minutes: number
  routing_provider: string
  is_route_fallback: boolean
  receiver_priority: number
  receiver_category?: string | null
  score: number
  score_breakdown: ScoreBreakdown
  warnings: string[]
  explanation: string
  evaluated_at: string
}

export interface MatchingQueryResponse {
  source_type: 'SURPLUS_LISTING' | 'DEMAND_REQUEST'
  source_id: string
  source_name: string
  total_candidates: number
  eligible_count: number
  ineligible_count: number
  review_required_count: number
  page: number
  page_size: number
  candidates: CandidateMatch[]
}

// =========================================================================
// MODULE 8: CONSTRAINED ALLOCATION OPTIMIZATION TYPES
// =========================================================================

export interface OptimizationRunRequest {
  surplus_listing_ids?: string[]
  demand_request_ids?: string[]
  timeout_seconds?: number
  max_distance_km?: number
  evaluation_time?: string
}

export interface AllocationItemDetail {
  item_id?: string
  proposal_id?: string
  surplus_listing_id: string
  demand_request_id: string
  supplier_id: string
  receiver_id: string
  supplier_name: string
  receiver_name: string
  item_name: string
  food_category: string
  allocated_quantity_kg: number
  estimated_distance_km: number
  estimated_transit_minutes: number
  urgency_at_allocation: string
  shelf_life_slack_minutes?: number | null
  allocation_score: number
  explanation: string
}

export interface UnfulfilledDemandDetail {
  demand_request_id: string
  receiver_id: string
  receiver_name: string
  food_category: string
  item_name?: string | null
  requested_quantity_kg: number
  fulfilled_in_proposal_kg: number
  unfulfilled_quantity_kg: number
  reason_code: string
  diagnostic_explanation: string
}

export interface UnallocatedSurplusDetail {
  surplus_listing_id: string
  supplier_id: string
  supplier_name: string
  food_category: string
  item_name: string
  available_quantity_kg: number
  allocated_in_proposal_kg: number
  unallocated_quantity_kg: number
  urgency: string
  reason_code: string
  diagnostic_explanation: string
}

export interface SolverDiagnostics {
  solver_name: string
  solver_status: string
  solve_time_ms: number
  num_surplus_considered: number
  num_demands_considered: number
  num_candidate_pairs: number
  num_variables: number
  num_constraints: number
  objective_value?: number | null
}

export interface OptimizationProposalResponse {
  proposal_id?: string | null
  status: string
  total_allocated_kg: number
  total_unallocated_kg: number
  total_unmet_demand_kg: number
  estimated_total_transit_km: number
  solver_status: string
  solve_time_ms: number
  ai_justification: string
  items: AllocationItemDetail[]
  unfulfilled_demands: UnfulfilledDemandDetail[]
  unallocated_surplus: UnallocatedSurplusDetail[]
  diagnostics: SolverDiagnostics
  created_at: string
}

// =============================================================================
// MODULE 9: AI REDISTRIBUTION AGENT & TOOL ORCHESTRATION
// =============================================================================

export interface ToolCallRecord {
  call_id: string
  tool_name: string
  arguments: Record<string, unknown>
}

export interface ToolResultRecord {
  call_id: string
  tool_name: string
  output: Record<string, unknown>
  success: boolean
  error?: string | null
}

export interface ProposalPreview {
  proposal_id?: string | null
  status: string
  banner: string
  total_allocated_kg: number
  total_unallocated_kg: number
  total_unmet_demand_kg: number
  solver_status: string
  item_count: number
  explanation: string
}

export interface ChatRequest {
  message: string
  conversation_id?: string | null
}

export interface ChatResponse {
  conversation_id: string
  message_id: string
  response_text: string
  tool_calls: ToolCallRecord[]
  tool_results: ToolResultRecord[]
  proposal_preview?: ProposalPreview | null
  ai_provider: string
  fallback_mode: boolean
  created_at: string
}

export interface ConversationMessageResponse {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  tool_calls?: ToolCallRecord[] | null
  tool_results?: ToolResultRecord[] | null
  proposal_id?: string | null
  created_at: string
}

export interface ConversationSummary {
  id: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
}

export interface ConversationDetailResponse {
  id: string
  title: string
  messages: ConversationMessageResponse[]
  created_at: string
  updated_at: string
}

export interface AgentToolDeclaration {
  name: string
  description: string
  parameters: Record<string, unknown>
}

// =============================================================================
// MODULE 10: HUMAN APPROVAL & REDISTRIBUTION TRANSACTIONS
// =============================================================================

export type ProposalStatus =
  | 'PENDING_REVIEW'
  | 'APPROVED'
  | 'ACCEPTED'
  | 'EXECUTING'
  | 'COMPLETED'
  | 'REJECTED'
  | 'CANCELLED'
  | 'FAILED'
  | 'SUPERSEDED'

export type TransactionStatus =
  | 'APPROVED'
  | 'SCHEDULED'
  | 'PICKUP_SCHEDULED'
  | 'DISPATCHED'
  | 'PICKED_UP'
  | 'IN_TRANSIT'
  | 'DELIVERED'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'

export interface ApproveProposalRequest {
  dispatch_notes?: string
  scheduled_pickup_at?: string
}

export interface RejectProposalRequest {
  reason: string
}

export interface UpdateTransactionStatusRequest {
  status: TransactionStatus
  reason?: string
  actual_pickup_at?: string
  actual_delivery_at?: string
  dispatch_notes?: string
  confirmed_returned_kg?: number
  actual_delivered_kg?: number
}

export interface TransactionStatusHistoryResponse {
  id: string
  previous_status?: string | null
  new_status: string
  changed_by_user_id: string
  reason?: string | null
  changed_at: string
}

export interface TransactionItemResponse {
  item_id: string
  surplus_listing_id: string
  demand_request_id: string
  supplier_id: string
  receiver_id: string
  supplier_name: string
  receiver_name: string
  item_name: string
  food_category: string
  allocated_quantity_kg: number
  estimated_distance_km: number
  estimated_transit_minutes: number
  urgency_at_allocation: string
}

export interface TransactionResponse {
  id: string
  proposal_id: string
  tracking_code: string
  status: TransactionStatus
  scheduled_pickup_at?: string | null
  actual_pickup_at?: string | null
  actual_delivery_at?: string | null
  dispatch_notes?: string | null
  total_allocated_kg: number
  items_count: number
  items: TransactionItemResponse[]
  status_history: TransactionStatusHistoryResponse[]
  created_at: string
  updated_at: string
}

export interface TransactionListResponse {
  total_count: number
  items: TransactionResponse[]
}

export interface ProposalActionResponse {
  proposal_id: string
  status: string
  message: string
  rejection_reason?: string | null
  transaction?: TransactionResponse | null
}





