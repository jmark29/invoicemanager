import { createBrowserRouter } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { InvoiceList } from '@/pages/InvoiceList'
import { InvoiceGenerate } from '@/pages/InvoiceGenerate'
import { InvoiceDetail } from '@/pages/InvoiceDetail'
import { ClientList, ClientDetail } from '@/pages/Clients'
import { CostCategories } from '@/pages/CostCategories'
import { CostCategoryDetail } from '@/pages/CostCategoryDetail'
import { ProviderInvoices } from '@/pages/ProviderInvoices'
import { BankTransactions } from '@/pages/BankTransactions'
import { UpworkTransactions } from '@/pages/UpworkTransactions'
import { Payments } from '@/pages/Payments'
import { Reconciliation } from '@/pages/Reconciliation'
import { InvoiceImport } from '@/pages/InvoiceImport'
import { CostReconciliation } from '@/pages/CostReconciliation'
import { Settings } from '@/pages/Settings'
import { NotFound } from '@/pages/NotFound'

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'invoices', element: <InvoiceList /> },
      { path: 'invoices/generate', element: <InvoiceGenerate /> },
      { path: 'invoices/import', element: <InvoiceImport /> },
      { path: 'invoices/:id', element: <InvoiceDetail /> },
      { path: 'reconciliation', element: <Reconciliation /> },
      { path: 'cost-reconciliation', element: <CostReconciliation /> },
      { path: 'clients', element: <ClientList /> },
      { path: 'clients/:id', element: <ClientDetail /> },
      { path: 'categories', element: <CostCategories /> },
      { path: 'categories/:id', element: <CostCategoryDetail /> },
      { path: 'provider-invoices', element: <ProviderInvoices /> },
      { path: 'bank-transactions', element: <BankTransactions /> },
      { path: 'upwork-transactions', element: <UpworkTransactions /> },
      { path: 'payments', element: <Payments /> },
      { path: 'settings', element: <Settings /> },
      { path: '*', element: <NotFound /> },
    ],
  },
])
