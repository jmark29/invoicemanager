import { createBrowserRouter } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { InvoiceList } from '@/pages/InvoiceList'
import { InvoiceGenerate } from '@/pages/InvoiceGenerate'
import { InvoiceDetail } from '@/pages/InvoiceDetail'
import { CostCategories } from '@/pages/CostCategories'
import { CostCategoryDetail } from '@/pages/CostCategoryDetail'
import { ProviderInvoices } from '@/pages/ProviderInvoices'
import { BankTransactions } from '@/pages/BankTransactions'
import { UpworkTransactions } from '@/pages/UpworkTransactions'
import { Payments } from '@/pages/Payments'
import { Reconciliation } from '@/pages/Reconciliation'
import { Settings } from '@/pages/Settings'
import { NotFound } from '@/pages/NotFound'

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'invoices', element: <InvoiceList /> },
      { path: 'invoices/generate', element: <InvoiceGenerate /> },
      { path: 'invoices/:id', element: <InvoiceDetail /> },
      { path: 'categories', element: <CostCategories /> },
      { path: 'categories/:id', element: <CostCategoryDetail /> },
      { path: 'provider-invoices', element: <ProviderInvoices /> },
      { path: 'bank-transactions', element: <BankTransactions /> },
      { path: 'upwork-transactions', element: <UpworkTransactions /> },
      { path: 'payments', element: <Payments /> },
      { path: 'reconciliation', element: <Reconciliation /> },
      { path: 'settings', element: <Settings /> },
      { path: '*', element: <NotFound /> },
    ],
  },
])
