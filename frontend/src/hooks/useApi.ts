import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  clientsApi, costCategoriesApi, lineItemDefsApi,
  providerInvoicesApi, bankTransactionsApi, upworkTransactionsApi,
  invoicesApi, paymentsApi, workingDaysApi, dashboardApi,
  companySettingsApi,
} from '@/api/client'
import type {
  ClientCreate, ClientUpdate,
  CostCategoryCreate, CostCategoryUpdate,
  LineItemDefinitionCreate, LineItemDefinitionUpdate,
  ProviderInvoiceCreate, ProviderInvoiceUpdate,
  BankTransactionUpdate,
  UpworkTransactionUpdate,
  CompanySettingsUpdate,
  InvoicePreviewRequest, InvoiceGenerateRequest, InvoiceStatusUpdate, InvoiceRegenerateRequest,
  PaymentReceiptCreate, PaymentReceiptUpdate,
  BulkUploadConfirmItem,
} from '@/types/api'

// ── Query keys ─────────────────────────────────────────────────

export const queryKeys = {
  clients: ['clients'] as const,
  client: (id: string) => ['clients', id] as const,
  costCategories: ['costCategories'] as const,
  costCategory: (id: string) => ['costCategories', id] as const,
  lineItemDefs: (clientId?: string) => ['lineItemDefs', clientId] as const,
  providerInvoices: (params?: Record<string, unknown>) => ['providerInvoices', params] as const,
  bankTransactions: (params?: Record<string, unknown>) => ['bankTransactions', params] as const,
  upworkTransactions: (params?: Record<string, unknown>) => ['upworkTransactions', params] as const,
  invoices: (params?: Record<string, unknown>) => ['invoices', params] as const,
  invoice: (id: number) => ['invoice', id] as const,
  payments: (params?: Record<string, unknown>) => ['payments', params] as const,
  workingDays: (year: number, month: number) => ['workingDays', year, month] as const,
  dashboardMonthly: (year: number, month: number) => ['dashboardMonthly', year, month] as const,
  dashboardOpenInvoices: ['dashboardOpenInvoices'] as const,
  dashboardReconciliation: (year: number, month: number) => ['dashboardReconciliation', year, month] as const,
}

// ── Clients ────────────────────────────────────────────────────

export function useClients(activeOnly = false) {
  return useQuery({
    queryKey: queryKeys.clients,
    queryFn: () => clientsApi.list(activeOnly),
  })
}

export function useClient(id: string) {
  return useQuery({
    queryKey: queryKeys.client(id),
    queryFn: () => clientsApi.get(id),
    enabled: !!id,
  })
}

export function useCreateClient() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ClientCreate) => clientsApi.create(data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: queryKeys.clients }) },
  })
}

export function useUpdateClient() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ClientUpdate }) => clientsApi.update(id, data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: queryKeys.clients }) },
  })
}

// ── Cost Categories ────────────────────────────────────────────

export function useCostCategories(activeOnly = false) {
  return useQuery({
    queryKey: queryKeys.costCategories,
    queryFn: () => costCategoriesApi.list(activeOnly),
  })
}

export function useCostCategory(id: string) {
  return useQuery({
    queryKey: queryKeys.costCategory(id),
    queryFn: () => costCategoriesApi.get(id),
    enabled: !!id,
  })
}

export function useCreateCostCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CostCategoryCreate) => costCategoriesApi.create(data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: queryKeys.costCategories }) },
  })
}

export function useUpdateCostCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CostCategoryUpdate }) => costCategoriesApi.update(id, data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: queryKeys.costCategories }) },
  })
}

// ── Line Item Definitions ──────────────────────────────────────

export function useLineItemDefs(clientId?: string) {
  return useQuery({
    queryKey: queryKeys.lineItemDefs(clientId),
    queryFn: () => lineItemDefsApi.list(clientId),
  })
}

export function useCreateLineItemDef() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LineItemDefinitionCreate) => lineItemDefsApi.create(data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['lineItemDefs'] }) },
  })
}

export function useUpdateLineItemDef() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: LineItemDefinitionUpdate }) => lineItemDefsApi.update(id, data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['lineItemDefs'] }) },
  })
}

export function useDeleteLineItemDef() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => lineItemDefsApi.delete(id),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['lineItemDefs'] }) },
  })
}

// ── Provider Invoices ──────────────────────────────────────────

export function useProviderInvoices(params?: { category_id?: string; assigned_month?: string }) {
  return useQuery({
    queryKey: queryKeys.providerInvoices(params),
    queryFn: () => providerInvoicesApi.list(params),
  })
}

export function useCreateProviderInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ProviderInvoiceCreate) => providerInvoicesApi.create(data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['providerInvoices'] }) },
  })
}

export function useUpdateProviderInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProviderInvoiceUpdate }) => providerInvoicesApi.update(id, data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['providerInvoices'] }) },
  })
}

export function useDeleteProviderInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => providerInvoicesApi.delete(id),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['providerInvoices'] }) },
  })
}

export function useUploadProviderInvoicePdf() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => providerInvoicesApi.uploadPdf(id, file),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['providerInvoices'] }) },
  })
}

export function useBulkUpload() {
  return useMutation({
    mutationFn: ({ files, categoryId }: { files: File[]; categoryId?: string }) =>
      providerInvoicesApi.bulkUpload(files, categoryId),
  })
}

export function useBulkConfirm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (items: BulkUploadConfirmItem[]) => providerInvoicesApi.bulkConfirm(items),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['providerInvoices'] }) },
  })
}

// ── Bank Transactions ──────────────────────────────────────────

export function useBankTransactions(params?: { category_id?: string; provider_invoice_id?: number }) {
  return useQuery({
    queryKey: queryKeys.bankTransactions(params),
    queryFn: () => bankTransactionsApi.list(params),
  })
}

export function useUpdateBankTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: BankTransactionUpdate }) => bankTransactionsApi.update(id, data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['bankTransactions'] }) },
  })
}

export function useImportBankXlsx() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ file, forceImportAll = false }: { file: File; forceImportAll?: boolean }) =>
      bankTransactionsApi.importXlsx(file, forceImportAll),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['bankTransactions'] })
      void qc.invalidateQueries({ queryKey: ['bankImportHistory'] })
    },
  })
}

export function useBankImportHistory() {
  return useQuery({
    queryKey: ['bankImportHistory'],
    queryFn: () => bankTransactionsApi.importHistory(),
  })
}

export function useConfirmMatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ txId, invoiceId }: { txId: number; invoiceId: number }) =>
      bankTransactionsApi.confirmMatch(txId, invoiceId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['dashboardReconciliation'] })
      void qc.invalidateQueries({ queryKey: ['bankTransactions'] })
      void qc.invalidateQueries({ queryKey: ['providerInvoices'] })
    },
  })
}

export function useRejectMatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (txId: number) => bankTransactionsApi.rejectMatch(txId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['dashboardReconciliation'] })
      void qc.invalidateQueries({ queryKey: ['bankTransactions'] })
    },
  })
}

export function useManualMatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ txId, invoiceId, bankFee }: { txId: number; invoiceId: number; bankFee?: number }) =>
      bankTransactionsApi.manualMatch(txId, invoiceId, bankFee),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['dashboardReconciliation'] })
      void qc.invalidateQueries({ queryKey: ['bankTransactions'] })
      void qc.invalidateQueries({ queryKey: ['providerInvoices'] })
    },
  })
}

// ── Upwork Transactions ────────────────────────────────────────

export function useUpworkTransactions(params?: { assigned_month?: string; category_id?: string }) {
  return useQuery({
    queryKey: queryKeys.upworkTransactions(params),
    queryFn: () => upworkTransactionsApi.list(params),
  })
}

export function useUpdateUpworkTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpworkTransactionUpdate }) => upworkTransactionsApi.update(id, data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['upworkTransactions'] }) },
  })
}

export function useImportUpworkXlsx() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ file, categoryId }: { file: File; categoryId?: string }) =>
      upworkTransactionsApi.importXlsx(file, categoryId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['upworkTransactions'] })
      void qc.invalidateQueries({ queryKey: ['upworkImportHistory'] })
    },
  })
}

export function useUpworkImportHistory() {
  return useQuery({
    queryKey: ['upworkImportHistory'],
    queryFn: () => upworkTransactionsApi.importHistory(),
  })
}

// ── Invoices (Generated) ──────────────────────────────────────

export function useInvoices(params?: { client_id?: string; status?: string; year?: number }) {
  return useQuery({
    queryKey: queryKeys.invoices(params),
    queryFn: () => invoicesApi.list(params),
  })
}

export function useInvoice(id: number) {
  return useQuery({
    queryKey: queryKeys.invoice(id),
    queryFn: () => invoicesApi.get(id),
    enabled: id > 0,
  })
}

export function useInvoicePreview() {
  return useMutation({
    mutationFn: (data: InvoicePreviewRequest) => invoicesApi.preview(data),
  })
}

export function useGenerateInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: InvoiceGenerateRequest) => invoicesApi.generate(data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['invoices'] }) },
  })
}

export function useUpdateInvoiceStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: InvoiceStatusUpdate }) => invoicesApi.updateStatus(id, data),
    onSuccess: (_, { id }) => {
      void qc.invalidateQueries({ queryKey: ['invoices'] })
      void qc.invalidateQueries({ queryKey: queryKeys.invoice(id) })
    },
  })
}

// ── Payments ───────────────────────────────────────────────────

export function usePayments(params?: { client_id?: string; matched_invoice_id?: number }) {
  return useQuery({
    queryKey: queryKeys.payments(params),
    queryFn: () => paymentsApi.list(params),
  })
}

export function useCreatePayment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: PaymentReceiptCreate) => paymentsApi.create(data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['payments'] }) },
  })
}

export function useUpdatePayment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: PaymentReceiptUpdate }) => paymentsApi.update(id, data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['payments'] }) },
  })
}

export function useDeletePayment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => paymentsApi.delete(id),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['payments'] }) },
  })
}

// ── Working Days ───────────────────────────────────────────────

export function useWorkingDays(year: number, month: number) {
  return useQuery({
    queryKey: queryKeys.workingDays(year, month),
    queryFn: () => workingDaysApi.get(year, month),
    enabled: month >= 1 && month <= 12,
  })
}

// ── Dashboard ─────────────────────────────────────────────────

export function useDashboardMonthly(year: number, month: number) {
  return useQuery({
    queryKey: queryKeys.dashboardMonthly(year, month),
    queryFn: () => dashboardApi.monthly(year, month),
    enabled: month >= 1 && month <= 12,
  })
}

export function useDashboardOpenInvoices() {
  return useQuery({
    queryKey: queryKeys.dashboardOpenInvoices,
    queryFn: () => dashboardApi.openInvoices(),
  })
}

export function useDashboardReconciliation(year: number, month: number) {
  return useQuery({
    queryKey: queryKeys.dashboardReconciliation(year, month),
    queryFn: () => dashboardApi.reconciliation(year, month),
    enabled: month >= 1 && month <= 12,
  })
}

// ── Invoice Regeneration ──────────────────────────────────────

export function useRegenerateInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: InvoiceRegenerateRequest }) =>
      invoicesApi.regenerate(id, data),
    onSuccess: (_, { id }) => {
      void qc.invalidateQueries({ queryKey: ['invoices'] })
      void qc.invalidateQueries({ queryKey: queryKeys.invoice(id) })
      void qc.invalidateQueries({ queryKey: ['dashboardMonthly'] })
      void qc.invalidateQueries({ queryKey: ['dashboardOpenInvoices'] })
    },
  })
}

// ── Company Settings ──────────────────────────────────────────

export function useCompanySettings() {
  return useQuery({
    queryKey: ['companySettings'],
    queryFn: () => companySettingsApi.get(),
  })
}

export function useUpdateCompanySettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CompanySettingsUpdate) => companySettingsApi.update(data),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['companySettings'] }) },
  })
}
