import axios from 'axios'
import type {
  HealthResponse,
  AppInfoResponse,
  TokenResponse,
  UserPublic,
  SupplierProfile,
  SupplierProfileCreatePayload,
  SupplierProfileUpdatePayload,
  ReceiverProfile,
  ReceiverProfileCreatePayload,
  ReceiverProfileUpdatePayload,
  SurplusListing,
  SurplusListingCreatePayload,
  SurplusListingUpdatePayload,
  SurplusPaginationResponse,
  DemandRequest,
  DemandRequestCreatePayload,
  DemandRequestUpdatePayload,
  DemandPaginationResponse,
  PerishabilityEvaluation,
  BatchEvaluationResponse,
  RouteEstimateRequest,
  RouteEstimateResult,
  MatchingQueryResponse,
  OptimizationRunRequest,
  OptimizationProposalResponse,
  ChatRequest,
  ChatResponse,
  ConversationSummary,
  ConversationDetailResponse,
  AgentToolDeclaration,
  ApproveProposalRequest,
  RejectProposalRequest,
  UpdateTransactionStatusRequest,
  TransactionResponse,
  TransactionListResponse,
  ProposalActionResponse,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const DEFAULT_API_TIMEOUT_MS = 8000
export const EXTENDED_API_TIMEOUT_MS = 60000

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: DEFAULT_API_TIMEOUT_MS,
})

// Attach Bearer JWT token from localStorage if present
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('fhd_token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const apiService = {
  // General & Health
  async getRoot(): Promise<AppInfoResponse> {
    const response = await apiClient.get<AppInfoResponse>('/')
    return response.data
  },

  async getHealth(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/health')
    return response.data
  },

  // Authentication
  async register(data: {
    name: string
    email: string
    password: string
    role: 'SUPPLIER' | 'RECEIVER'
  }): Promise<{ user_id: string; email: string; role: string; message: string }> {
    const response = await apiClient.post('/api/v1/auth/register', data)
    return response.data
  },

  async login(data: { email: string; password: string }): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>('/api/v1/auth/login', data)
    return response.data
  },

  async getMe(): Promise<UserPublic> {
    const response = await apiClient.get<UserPublic>('/api/v1/auth/me')
    return response.data
  },

  // Supplier Profile
  async getSupplierProfile(): Promise<SupplierProfile> {
    const response = await apiClient.get<SupplierProfile>('/api/v1/suppliers/profile')
    return response.data
  },

  async createSupplierProfile(data: SupplierProfileCreatePayload): Promise<SupplierProfile> {
    const response = await apiClient.post<SupplierProfile>('/api/v1/suppliers/profile', data)
    return response.data
  },

  async updateSupplierProfile(data: SupplierProfileUpdatePayload): Promise<SupplierProfile> {
    const response = await apiClient.patch<SupplierProfile>('/api/v1/suppliers/profile', data)
    return response.data
  },

  // Receiver Profile
  async getReceiverProfile(): Promise<ReceiverProfile> {
    const response = await apiClient.get<ReceiverProfile>('/api/v1/receivers/profile')
    return response.data
  },

  async createReceiverProfile(data: ReceiverProfileCreatePayload): Promise<ReceiverProfile> {
    const response = await apiClient.post<ReceiverProfile>('/api/v1/receivers/profile', data)
    return response.data
  },

  async updateReceiverProfile(data: ReceiverProfileUpdatePayload): Promise<ReceiverProfile> {
    const response = await apiClient.patch<ReceiverProfile>('/api/v1/receivers/profile', data)
    return response.data
  },

  // Surplus Inventory Management
  async getSurplusListings(params?: {
    page?: number
    page_size?: number
    status?: string
    food_category?: string
  }): Promise<SurplusPaginationResponse> {
    const response = await apiClient.get<SurplusPaginationResponse>('/api/v1/surplus-listings', {
      params,
    })
    return response.data
  },

  async getSurplusListing(id: string): Promise<SurplusListing> {
    const response = await apiClient.get<SurplusListing>(`/api/v1/surplus-listings/${id}`)
    return response.data
  },

  async createSurplusListing(data: SurplusListingCreatePayload): Promise<SurplusListing> {
    const response = await apiClient.post<SurplusListing>('/api/v1/surplus-listings', data)
    return response.data
  },

  async updateSurplusListing(
    id: string,
    data: SurplusListingUpdatePayload
  ): Promise<SurplusListing> {
    const response = await apiClient.patch<SurplusListing>(`/api/v1/surplus-listings/${id}`, data)
    return response.data
  },

  async pauseSurplusListing(id: string): Promise<SurplusListing> {
    const response = await apiClient.post<SurplusListing>(`/api/v1/surplus-listings/${id}/pause`)
    return response.data
  },

  async resumeSurplusListing(id: string): Promise<SurplusListing> {
    const response = await apiClient.post<SurplusListing>(`/api/v1/surplus-listings/${id}/resume`)
    return response.data
  },

  async cancelSurplusListing(id: string): Promise<SurplusListing> {
    const response = await apiClient.post<SurplusListing>(`/api/v1/surplus-listings/${id}/cancel`)
    return response.data
  },

  // Demand Request Management
  async getDemandRequests(params?: {
    page?: number
    page_size?: number
    status?: string
    food_category?: string
  }): Promise<DemandPaginationResponse> {
    const response = await apiClient.get<DemandPaginationResponse>('/api/v1/demand-requests', {
      params,
    })
    return response.data
  },

  async getDemandRequest(id: string): Promise<DemandRequest> {
    const response = await apiClient.get<DemandRequest>(`/api/v1/demand-requests/${id}`)
    return response.data
  },

  async createDemandRequest(data: DemandRequestCreatePayload): Promise<DemandRequest> {
    const response = await apiClient.post<DemandRequest>('/api/v1/demand-requests', data)
    return response.data
  },

  async updateDemandRequest(
    id: string,
    data: DemandRequestUpdatePayload
  ): Promise<DemandRequest> {
    const response = await apiClient.patch<DemandRequest>(`/api/v1/demand-requests/${id}`, data)
    return response.data
  },

  async pauseDemandRequest(id: string): Promise<DemandRequest> {
    const response = await apiClient.post<DemandRequest>(`/api/v1/demand-requests/${id}/pause`)
    return response.data
  },

  async resumeDemandRequest(id: string): Promise<DemandRequest> {
    const response = await apiClient.post<DemandRequest>(`/api/v1/demand-requests/${id}/resume`)
    return response.data
  },

  async cancelDemandRequest(id: string): Promise<DemandRequest> {
    const response = await apiClient.post<DemandRequest>(`/api/v1/demand-requests/${id}/cancel`)
    return response.data
  },

  // Perishability Intelligence
  async getListingPerishability(listingId: string): Promise<PerishabilityEvaluation> {
    const response = await apiClient.get<PerishabilityEvaluation>(
      `/api/v1/intelligence/perishability/${listingId}`
    )
    return response.data
  },

  async getBatchActivePerishability(): Promise<BatchEvaluationResponse> {
    const response = await apiClient.get<BatchEvaluationResponse>(
      '/api/v1/intelligence/perishability/batch-active'
    )
    return response.data
  },

  // Geospatial Routing
  async getReceiversDirectory(): Promise<ReceiverProfile[]> {
    const response = await apiClient.get<ReceiverProfile[]>('/api/v1/receivers/directory')
    return response.data
  },

  async estimateRoute(data: RouteEstimateRequest): Promise<RouteEstimateResult> {
    const response = await apiClient.post<RouteEstimateResult>(
      '/api/v1/geospatial/route-estimate',
      data
    )
    return response.data
  },

  // Multi-Factor Supply-Demand Matching
  async getListingCandidates(
    listingId: string,
    params?: { page?: number; page_size?: number; include_ineligible?: boolean }
  ): Promise<MatchingQueryResponse> {
    const response = await apiClient.get<MatchingQueryResponse>(
      `/api/v1/matching/listings/${listingId}/candidates`,
      { params, timeout: EXTENDED_API_TIMEOUT_MS }
    )
    return response.data
  },

  async getDemandCandidates(
    demandId: string,
    params?: { page?: number; page_size?: number; include_ineligible?: boolean }
  ): Promise<MatchingQueryResponse> {
    const response = await apiClient.get<MatchingQueryResponse>(
      `/api/v1/matching/demands/${demandId}/candidates`,
      { params, timeout: EXTENDED_API_TIMEOUT_MS }
    )
    return response.data
  },

  // Module 8: Google OR-Tools Allocation Optimization
  async createAllocationProposal(
    data: OptimizationRunRequest
  ): Promise<OptimizationProposalResponse> {
    const response = await apiClient.post<OptimizationProposalResponse>(
      '/api/v1/optimization/allocation-proposals',
      data,
      { timeout: EXTENDED_API_TIMEOUT_MS }
    )
    return response.data
  },

  async getAllocationProposal(
    proposalId: string
  ): Promise<OptimizationProposalResponse> {
    const response = await apiClient.get<OptimizationProposalResponse>(
      `/api/v1/optimization/proposals/${proposalId}`,
      { timeout: EXTENDED_API_TIMEOUT_MS }
    )
    return response.data
  },

  // Module 9: AI Redistribution Agent
  async sendChatMessage(data: ChatRequest): Promise<ChatResponse> {
    const response = await apiClient.post<ChatResponse>('/api/v1/agent/chat', data)
    return response.data
  },

  async listConversations(limit = 50): Promise<ConversationSummary[]> {
    const response = await apiClient.get<ConversationSummary[]>('/api/v1/agent/conversations', {
      params: { limit },
    })
    return response.data
  },

  async getConversation(conversationId: string): Promise<ConversationDetailResponse> {
    const response = await apiClient.get<ConversationDetailResponse>(
      `/api/v1/agent/conversations/${conversationId}`
    )
    return response.data
  },

  async deleteConversation(
    conversationId: string
  ): Promise<{ deleted: boolean; conversation_id: string }> {
    const response = await apiClient.delete<{ deleted: boolean; conversation_id: string }>(
      `/api/v1/agent/conversations/${conversationId}`
    )
    return response.data
  },

  async listAuthorizedTools(): Promise<AgentToolDeclaration[]> {
    const response = await apiClient.get<AgentToolDeclaration[]>('/api/v1/agent/tools')
    return response.data
  },

  // Module 10: Human Approval & Redistribution Transactions
  async approveProposal(
    proposalId: string,
    data?: ApproveProposalRequest
  ): Promise<TransactionResponse | ProposalActionResponse> {
    const response = await apiClient.post<TransactionResponse | ProposalActionResponse>(
      `/api/v1/optimization/proposals/${proposalId}/approve`,
      data || {}
    )
    return response.data
  },

  async rejectProposal(
    proposalId: string,
    data: RejectProposalRequest
  ): Promise<ProposalActionResponse> {
    const response = await apiClient.post<ProposalActionResponse>(
      `/api/v1/optimization/proposals/${proposalId}/reject`,
      data
    )
    return response.data
  },

  async listTransactions(params?: {
    status?: string
    limit?: number
    offset?: number
  }): Promise<TransactionListResponse> {
    const response = await apiClient.get<TransactionListResponse>('/api/v1/transactions', {
      params,
    })
    return response.data
  },

  async getTransaction(id: string): Promise<TransactionResponse> {
    const response = await apiClient.get<TransactionResponse>(`/api/v1/transactions/${id}`)
    return response.data
  },

  async executeTransaction(id: string): Promise<TransactionResponse> {
    const response = await apiClient.post<TransactionResponse>(
      `/api/v1/transactions/${id}/execute`
    )
    return response.data
  },

  async updateTransactionStatus(
    id: string,
    data: UpdateTransactionStatusRequest
  ): Promise<TransactionResponse> {
    const response = await apiClient.patch<TransactionResponse>(
      `/api/v1/transactions/${id}/status`,
      data
    )
    return response.data
  },
}
