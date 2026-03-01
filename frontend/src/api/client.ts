import type {
  Client, ClientCreate, ClientUpdate,
  CostCategory, CostCategoryCreate, CostCategoryUpdate,
  LineItemDefinition, LineItemDefinitionCreate, LineItemDefinitionUpdate,
  ProviderInvoice, ProviderInvoiceCreate, ProviderInvoiceUpdate,
  BankTransaction, BankTransactionCreate, BankTransactionUpdate, BankImportResponse,
  UpworkTransaction, UpworkTransactionUpdate, UpworkImportResponse,
  ImportHistoryItem,
  CompanySettings, CompanySettingsUpdate,
  PaymentReceipt, PaymentReceiptCreate, PaymentReceiptUpdate,
  GeneratedInvoice, GeneratedInvoiceListItem,
  InvoicePreviewRequest, InvoicePreviewResponse,
  InvoiceGenerateRequest, InvoiceRegenerateRequest, InvoiceStatusUpdate,
  MonthlyDashboard, OpenInvoicesData, ReconciliationData,
  MatchActionResponse,
  WorkingDaysResponse,
  BulkUploadResponse, BulkUploadConfirmItem, BulkUploadConfirmResponse,
} from '@/types/api'

// ── Base helpers ───────────────────────────────────────────────

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string }
    throw new Error(body.detail ?? `API error ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

async function apiUpload<T>(
  url: string,
  file: File,
  extraParams?: Record<string, string>,
): Promise<T> {
  const formData = new FormData()
  formData.append('file', file)
  const params = extraParams ? '?' + new URLSearchParams(extraParams).toString() : ''
  const res = await fetch(url + params, { method: 'POST', body: formData })
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string }
    throw new Error(body.detail ?? `Upload error ${res.status}`)
  }
  return res.json() as Promise<T>
}

function buildQs(params?: Record<string, string | number | boolean | null | undefined>): string {
  if (!params) return ''
  const entries = Object.entries(params).filter(([, v]) => v != null) as [string, string | number | boolean][]
  if (entries.length === 0) return ''
  return '?' + new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()
}

// ── Clients ────────────────────────────────────────────────────

export const clientsApi = {
  list: (activeOnly = false) =>
    apiFetch<Client[]>(`/api/clients${buildQs({ active_only: activeOnly || undefined })}`),
  get: (id: string) =>
    apiFetch<Client>(`/api/clients/${id}`),
  create: (data: ClientCreate) =>
    apiFetch<Client>('/api/clients', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: ClientUpdate) =>
    apiFetch<Client>(`/api/clients/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
}

// ── Cost Categories ────────────────────────────────────────────

export const costCategoriesApi = {
  list: (activeOnly = false) =>
    apiFetch<CostCategory[]>(`/api/cost-categories${buildQs({ active_only: activeOnly || undefined })}`),
  get: (id: string) =>
    apiFetch<CostCategory>(`/api/cost-categories/${id}`),
  create: (data: CostCategoryCreate) =>
    apiFetch<CostCategory>('/api/cost-categories', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: CostCategoryUpdate) =>
    apiFetch<CostCategory>(`/api/cost-categories/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
}

// ── Line Item Definitions ──────────────────────────────────────

export const lineItemDefsApi = {
  list: (clientId?: string) =>
    apiFetch<LineItemDefinition[]>(`/api/line-item-definitions${buildQs({ client_id: clientId })}`),
  get: (id: number) =>
    apiFetch<LineItemDefinition>(`/api/line-item-definitions/${id}`),
  create: (data: LineItemDefinitionCreate) =>
    apiFetch<LineItemDefinition>('/api/line-item-definitions', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: LineItemDefinitionUpdate) =>
    apiFetch<LineItemDefinition>(`/api/line-item-definitions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) =>
    apiFetch<void>(`/api/line-item-definitions/${id}`, { method: 'DELETE' }),
}

// ── Provider Invoices ──────────────────────────────────────────

export const providerInvoicesApi = {
  list: (params?: { category_id?: string; assigned_month?: string }) =>
    apiFetch<ProviderInvoice[]>(`/api/provider-invoices${buildQs(params)}`),
  get: (id: number) =>
    apiFetch<ProviderInvoice>(`/api/provider-invoices/${id}`),
  create: (data: ProviderInvoiceCreate) =>
    apiFetch<ProviderInvoice>('/api/provider-invoices', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: ProviderInvoiceUpdate) =>
    apiFetch<ProviderInvoice>(`/api/provider-invoices/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) =>
    apiFetch<void>(`/api/provider-invoices/${id}`, { method: 'DELETE' }),
  uploadPdf: (id: number, file: File) =>
    apiUpload<ProviderInvoice>(`/api/provider-invoices/${id}/upload`, file),
  downloadUrl: (id: number) => `/api/provider-invoices/${id}/download`,
  bulkUpload: async (files: File[], categoryId?: string): Promise<BulkUploadResponse> => {
    const formData = new FormData()
    for (const file of files) formData.append('files', file)
    const params = categoryId ? `?category_id=${encodeURIComponent(categoryId)}` : ''
    const res = await fetch(`/api/provider-invoices/bulk-upload${params}`, { method: 'POST', body: formData })
    if (!res.ok) {
      const body = await res.json().catch(() => ({})) as { detail?: string }
      throw new Error(body.detail ?? `Upload error ${res.status}`)
    }
    return res.json() as Promise<BulkUploadResponse>
  },
  bulkConfirm: (items: BulkUploadConfirmItem[]) =>
    apiFetch<BulkUploadConfirmResponse>('/api/provider-invoices/bulk-confirm', {
      method: 'POST',
      body: JSON.stringify({ items }),
    }),
}

// ── Bank Transactions ──────────────────────────────────────────

export const bankTransactionsApi = {
  list: (params?: { category_id?: string; provider_invoice_id?: number }) =>
    apiFetch<BankTransaction[]>(`/api/bank-transactions${buildQs(params)}`),
  get: (id: number) =>
    apiFetch<BankTransaction>(`/api/bank-transactions/${id}`),
  create: (data: BankTransactionCreate) =>
    apiFetch<BankTransaction>('/api/bank-transactions', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: BankTransactionUpdate) =>
    apiFetch<BankTransaction>(`/api/bank-transactions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  importXlsx: (file: File, forceImportAll = false) =>
    apiUpload<BankImportResponse>(
      '/api/bank-transactions/import',
      file,
      forceImportAll ? { force_import_all: 'true' } : undefined,
    ),
  importHistory: () =>
    apiFetch<ImportHistoryItem[]>('/api/bank-transactions/import-history'),
  confirmMatch: (txId: number, invoiceId: number) =>
    apiFetch<MatchActionResponse>(`/api/bank-transactions/${txId}/match`, {
      method: 'POST',
      body: JSON.stringify({ action: 'confirm', provider_invoice_id: invoiceId }),
    }),
  rejectMatch: (txId: number) =>
    apiFetch<{ match_status: string }>(`/api/bank-transactions/${txId}/match`, {
      method: 'POST',
      body: JSON.stringify({ action: 'reject' }),
    }),
  manualMatch: (txId: number, invoiceId: number, bankFee?: number) =>
    apiFetch<MatchActionResponse>(`/api/bank-transactions/${txId}/manual-match`, {
      method: 'POST',
      body: JSON.stringify({ provider_invoice_id: invoiceId, bank_fee: bankFee }),
    }),
}

// ── Upwork Transactions ────────────────────────────────────────

export const upworkTransactionsApi = {
  list: (params?: { assigned_month?: string; category_id?: string }) =>
    apiFetch<UpworkTransaction[]>(`/api/upwork-transactions${buildQs(params)}`),
  get: (id: number) =>
    apiFetch<UpworkTransaction>(`/api/upwork-transactions/${id}`),
  update: (id: number, data: UpworkTransactionUpdate) =>
    apiFetch<UpworkTransaction>(`/api/upwork-transactions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  importXlsx: (file: File, categoryId?: string) =>
    apiUpload<UpworkImportResponse>(
      '/api/upwork-transactions/import',
      file,
      categoryId ? { category_id: categoryId } : undefined,
    ),
  importHistory: () =>
    apiFetch<ImportHistoryItem[]>('/api/upwork-transactions/import-history'),
}

// ── Invoices (Generated) ──────────────────────────────────────

export const invoicesApi = {
  list: (params?: { client_id?: string; status?: string; year?: number }) =>
    apiFetch<GeneratedInvoiceListItem[]>(`/api/invoices${buildQs(params)}`),
  get: (id: number) =>
    apiFetch<GeneratedInvoice>(`/api/invoices/${id}`),
  preview: (data: InvoicePreviewRequest) =>
    apiFetch<InvoicePreviewResponse>('/api/invoices/preview', { method: 'POST', body: JSON.stringify(data) }),
  generate: (data: InvoiceGenerateRequest) =>
    apiFetch<GeneratedInvoice>('/api/invoices', { method: 'POST', body: JSON.stringify(data) }),
  updateStatus: (id: number, data: InvoiceStatusUpdate) =>
    apiFetch<GeneratedInvoice>(`/api/invoices/${id}/status`, { method: 'PATCH', body: JSON.stringify(data) }),
  regenerate: (id: number, data: InvoiceRegenerateRequest) =>
    apiFetch<GeneratedInvoice>(`/api/invoices/${id}/regenerate`, { method: 'POST', body: JSON.stringify(data) }),
  downloadUrl: (id: number) => `/api/invoices/${id}/download`,
}

// ── Payments ───────────────────────────────────────────────────

export const paymentsApi = {
  list: (params?: { client_id?: string; matched_invoice_id?: number }) =>
    apiFetch<PaymentReceipt[]>(`/api/payments${buildQs(params)}`),
  get: (id: number) =>
    apiFetch<PaymentReceipt>(`/api/payments/${id}`),
  create: (data: PaymentReceiptCreate) =>
    apiFetch<PaymentReceipt>('/api/payments', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: PaymentReceiptUpdate) =>
    apiFetch<PaymentReceipt>(`/api/payments/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) =>
    apiFetch<void>(`/api/payments/${id}`, { method: 'DELETE' }),
}

// ── Working Days ───────────────────────────────────────────────

export const workingDaysApi = {
  get: (year: number, month: number) =>
    apiFetch<WorkingDaysResponse>(`/api/working-days/${year}/${month}`),
}

// ── Dashboard ─────────────────────────────────────────────────

export const dashboardApi = {
  monthly: (year: number, month: number) =>
    apiFetch<MonthlyDashboard>(`/api/dashboard/monthly/${year}/${month}`),
  openInvoices: () =>
    apiFetch<OpenInvoicesData>('/api/dashboard/open-invoices'),
  reconciliation: (year: number, month: number) =>
    apiFetch<ReconciliationData>(`/api/dashboard/reconciliation/${year}/${month}`),
}

// ── Company Settings ──────────────────────────────────────────

export const companySettingsApi = {
  get: () =>
    apiFetch<CompanySettings>('/api/settings/company'),
  update: (data: CompanySettingsUpdate) =>
    apiFetch<CompanySettings>('/api/settings/company', { method: 'PATCH', body: JSON.stringify(data) }),
}

// ── Health ─────────────────────────────────────────────────────

export const healthApi = {
  check: () => apiFetch<{ status: string }>('/api/health'),
}
