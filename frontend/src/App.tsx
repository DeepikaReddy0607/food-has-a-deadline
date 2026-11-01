import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import { RootLayout } from '@/layouts/RootLayout'
import { HomePage } from '@/pages/HomePage'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { ProtectedRoute } from '@/components/ProtectedRoute'

// Profile Pages
import { SupplierProfileView } from '@/pages/supplier/SupplierProfileView'
import { SupplierProfileSetup } from '@/pages/supplier/SupplierProfileSetup'
import { SupplierProfileEdit } from '@/pages/supplier/SupplierProfileEdit'
import { ReceiverProfileView } from '@/pages/receiver/ReceiverProfileView'
import { ReceiverProfileSetup } from '@/pages/receiver/ReceiverProfileSetup'
import { ReceiverProfileEdit } from '@/pages/receiver/ReceiverProfileEdit'

// Module 4: Supplier Surplus Inventory Pages
import { MySurplusInventory } from '@/pages/supplier/MySurplusInventory'
import { CreateSurplusListing } from '@/pages/supplier/CreateSurplusListing'
import { SurplusListingDetails } from '@/pages/supplier/SurplusListingDetails'
import { EditSurplusListing } from '@/pages/supplier/EditSurplusListing'

// Module 4: Receiver Food Demand Pages
import { MyDemandRequests } from '@/pages/receiver/MyDemandRequests'
import { CreateDemandRequest } from '@/pages/receiver/CreateDemandRequest'
import { DemandDetails } from '@/pages/receiver/DemandDetails'
import { EditDemandRequest } from '@/pages/receiver/EditDemandRequest'

// Module 8 & 10: Coordinator Optimization Engine & Dispatch Transactions
import { OptimizationDashboard } from '@/pages/coordinator/OptimizationDashboard'
import { TransactionsDashboard } from '@/pages/coordinator/TransactionsDashboard'

// Module 9: AI Redistribution Agent
import { AssistantPage } from '@/pages/assistant/AssistantPage'

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<RootLayout />}>
            <Route index element={<HomePage />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="register" element={<RegisterPage />} />

            {/* Supplier Routes */}
            <Route element={<ProtectedRoute allowedRoles={['SUPPLIER', 'ADMIN']} />}>
              <Route path="supplier/profile" element={<SupplierProfileView />} />
              <Route path="supplier/profile/setup" element={<SupplierProfileSetup />} />
              <Route path="supplier/profile/edit" element={<SupplierProfileEdit />} />

              {/* Module 4 Operational Routes */}
              <Route path="supplier/inventory" element={<MySurplusInventory />} />
              <Route path="supplier/inventory/new" element={<CreateSurplusListing />} />
              <Route path="supplier/inventory/:id" element={<SurplusListingDetails />} />
              <Route path="supplier/inventory/:id/edit" element={<EditSurplusListing />} />
            </Route>

            {/* Receiver Routes */}
            <Route element={<ProtectedRoute allowedRoles={['RECEIVER', 'ADMIN']} />}>
              <Route path="receiver/profile" element={<ReceiverProfileView />} />
              <Route path="receiver/profile/setup" element={<ReceiverProfileSetup />} />
              <Route path="receiver/profile/edit" element={<ReceiverProfileEdit />} />

              {/* Module 4 Operational Routes */}
              <Route path="receiver/demands" element={<MyDemandRequests />} />
              <Route path="receiver/demands/new" element={<CreateDemandRequest />} />
              <Route path="receiver/demands/:id" element={<DemandDetails />} />
              <Route path="receiver/demands/:id/edit" element={<EditDemandRequest />} />
            </Route>

            {/* Coordinator & Admin Routes */}
            <Route element={<ProtectedRoute allowedRoles={['COORDINATOR', 'ADMIN']} />}>
              <Route path="coordinator/optimization" element={<OptimizationDashboard />} />
              <Route path="coordinator/transactions" element={<TransactionsDashboard />} />
            </Route>

            {/* Module 9: AI Redistribution Copilot (Authenticated) */}
            <Route element={<ProtectedRoute allowedRoles={['SUPPLIER', 'RECEIVER', 'COORDINATOR', 'ADMIN']} />}>
              <Route path="assistant" element={<AssistantPage />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
