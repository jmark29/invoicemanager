// TypeScript interfaces mirroring backend Pydantic schemas

// ── Client ─────────────────────────────────────────────────────

export interface Client {
  id: string
  client_number: string
  name: string
  address_line1: string
  address_line2: string | null
  zip_city: string
  vat_rate: number
  active: boolean
}

export interface ClientCreate {
  id: string
  client_number: string
  name: string
  address_line1: string
  address_line2?: string | null
  zip_city: string
  vat_rate?: number
  active?: boolean
}

export interface ClientUpdate {
  client_number?: string
  name?: string
  address_line1?: string
  address_line2?: string | null
  zip_city?: string
  vat_rate?: number
  active?: boolean
}

// ── Cost Category ──────────────────────────────────────────────

export interface CostCategory {
  id: string
  name: string
  provider_name: string | null
  provider_location: string | null
  currency: string
  hourly_rate: number | null
  rate_currency: string | null
  billing_cycle: string
  cost_type: string
  distribution_method: string | null
  vat_status: string
  bank_keywords: string[]
  notes: string | null
  active: boolean
  sort_order: number
}

export interface CostCategoryCreate {
  id: string
  name: string
  provider_name?: string | null
  provider_location?: string | null
  currency?: string
  hourly_rate?: number | null
  rate_currency?: string | null
  billing_cycle: string
  cost_type: string
  distribution_method?: string | null
  vat_status?: string
  bank_keywords?: string[]
  notes?: string | null
  active?: boolean
  sort_order?: number
}

export interface CostCategoryUpdate {
  name?: string
  provider_name?: string | null
  provider_location?: string | null
  currency?: string
  hourly_rate?: number | null
  rate_currency?: string | null
  billing_cycle?: string
  cost_type?: string
  distribution_method?: string | null
  vat_status?: string
  bank_keywords?: string[]
  notes?: string | null
  active?: boolean
  sort_order?: number
}

// ── Line Item Definition ───────────────────────────────────────

export interface LineItemDefinition {
  id: number
  client_id: string
  position: number
  label: string
  source_type: string
  category_id: string | null
  fixed_amount: number | null
  is_optional: boolean
  sort_order: number
}

export interface LineItemDefinitionCreate {
  client_id: string
  position: number
  label: string
  source_type: string
  category_id?: string | null
  fixed_amount?: number | null
  is_optional?: boolean
  sort_order?: number
}

export interface LineItemDefinitionUpdate {
  position?: number
  label?: string
  source_type?: string
  category_id?: string | null
  fixed_amount?: number | null
  is_optional?: boolean
  sort_order?: number
}

// ── Provider Invoice ───────────────────────────────────────────

export interface ProviderInvoice {
  id: number
  category_id: string
  invoice_number: string
  invoice_date: string
  period_start: string | null
  period_end: string | null
  covers_months: string[]
  assigned_month: string | null
  hours: number | null
  hourly_rate: number | null
  rate_currency: string | null
  amount: number
  currency: string
  file_path: string | null
  notes: string | null
  created_at: string
}

export interface ProviderInvoiceCreate {
  category_id: string
  invoice_number: string
  invoice_date: string
  period_start?: string | null
  period_end?: string | null
  covers_months?: string[]
  assigned_month?: string | null
  hours?: number | null
  hourly_rate?: number | null
  rate_currency?: string | null
  amount: number
  currency?: string
  notes?: string | null
}

export interface ProviderInvoiceUpdate {
  invoice_number?: string
  invoice_date?: string
  period_start?: string | null
  period_end?: string | null
  covers_months?: string[]
  assigned_month?: string | null
  hours?: number | null
  hourly_rate?: number | null
  rate_currency?: string | null
  amount?: number
  currency?: string
  notes?: string | null
}

// ── Bank Transaction ───────────────────────────────────────────

export interface BankTransaction {
  id: number
  booking_date: string
  value_date: string | null
  transaction_type: string | null
  description: string
  amount_eur: number
  reference: string | null
  account_iban: string | null
  category_id: string | null
  provider_invoice_id: number | null
  fx_rate: number | null
  bank_fee: number | null
  notes: string | null
}

export interface BankTransactionCreate {
  booking_date: string
  value_date?: string | null
  transaction_type?: string | null
  description: string
  amount_eur: number
  reference?: string | null
  account_iban?: string | null
  category_id?: string | null
  provider_invoice_id?: number | null
  fx_rate?: number | null
  bank_fee?: number | null
  notes?: string | null
}

export interface BankTransactionUpdate {
  category_id?: string | null
  provider_invoice_id?: number | null
  fx_rate?: number | null
  bank_fee?: number | null
  notes?: string | null
}

export interface BankImportResponse {
  imported: number
  skipped_duplicate: number
  auto_matched: number
  errors: string[]
}

// ── Upwork Transaction ─────────────────────────────────────────

export interface UpworkTransaction {
  id: number
  tx_id: string
  tx_date: string
  tx_type: string | null
  description: string | null
  period_start: string | null
  period_end: string | null
  amount_eur: number
  freelancer_name: string | null
  contract_ref: string | null
  category_id: string | null
  assigned_month: string | null
  assigned_invoice_id: number | null
}

export interface UpworkTransactionUpdate {
  category_id?: string | null
  assigned_month?: string | null
  assigned_invoice_id?: number | null
  freelancer_name?: string | null
  notes?: string | null
}

export interface UpworkImportResponse {
  imported: number
  skipped_duplicate: number
  skipped_no_amount: number
  skipped_no_period: number
  errors: string[]
}

// ── Generated Invoice ──────────────────────────────────────────

export interface GeneratedInvoiceItem {
  id: number
  invoice_id: number
  position: number
  label: string
  amount: number
  source_type: string
  category_id: string | null
  provider_invoice_id: number | null
  distribution_source_id: number | null
  distribution_months_json: string | null
  upwork_tx_ids_json: string | null
  notes: string | null
}

export interface GeneratedInvoice {
  id: number
  client_id: string
  invoice_number: string
  invoice_number_display: string | null
  filename: string | null
  period_year: number
  period_month: number
  invoice_date: string
  net_total: number
  vat_amount: number
  gross_total: number
  status: InvoiceStatus
  file_path: string | null
  pdf_path: string | null
  sent_date: string | null
  created_at: string
  notes: string | null
  items: GeneratedInvoiceItem[]
}

export interface GeneratedInvoiceListItem {
  id: number
  client_id: string
  invoice_number: string
  period_year: number
  period_month: number
  invoice_date: string
  net_total: number
  vat_amount: number
  gross_total: number
  status: InvoiceStatus
  created_at: string
}

export type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue'

// ── Invoice Preview / Generate ─────────────────────────────────

export interface InvoicePreviewRequest {
  client_id: string
  year: number
  month: number
}

export interface ResolvedLineItem {
  position: number
  label: string
  amount: number
  source_type: string
  category_id: string | null
  provider_invoice_id: number | null
  distribution_source_id: number | null
  distribution_months: string[] | null
  upwork_tx_ids: string[] | null
  warnings: string[]
}

export interface InvoicePreviewResponse {
  client_id: string
  year: number
  month: number
  items: ResolvedLineItem[]
  net_total: number
  vat_amount: number
  gross_total: number
  warnings: string[]
}

export interface InvoiceGenerateRequest {
  client_id: string
  year: number
  month: number
  invoice_number: string
  invoice_date: string
  overrides?: Record<number, number> | null
  notes?: string | null
}

export interface InvoiceStatusUpdate {
  status: InvoiceStatus
  sent_date?: string | null
}

export interface InvoiceRegenerateRequest {
  overrides?: Record<number, number> | null
  notes?: string | null
}

// ── Payment Receipt ────────────────────────────────────────────

export interface PaymentReceipt {
  id: number
  client_id: string
  payment_date: string
  amount_eur: number
  reference: string | null
  matched_invoice_id: number | null
  notes: string | null
}

export interface PaymentReceiptCreate {
  client_id: string
  payment_date: string
  amount_eur: number
  reference?: string | null
  matched_invoice_id?: number | null
  notes?: string | null
}

export interface PaymentReceiptUpdate {
  payment_date?: string
  amount_eur?: number
  reference?: string | null
  matched_invoice_id?: number | null
  notes?: string | null
}

// ── Dashboard ─────────────────────────────────────────────────

export interface MonthlyDashboard {
  year: number
  month: number
  has_invoice: boolean
  invoice: GeneratedInvoiceListItem | null
  items: GeneratedInvoiceItem[]
  net_total: number
  vat_amount: number
  gross_total: number
  payment_total: number
  payment_balance: number
}

export interface OpenInvoicesData {
  invoices: GeneratedInvoiceListItem[]
  count: number
  total_gross: number
  total_net: number
}

// ── Reconciliation ────────────────────────────────────────────

export interface ProviderInvoiceMatch {
  category_id: string
  category_name: string
  invoice_number: string
  invoice_amount: number
  has_bank_payment: boolean
  bank_amount: number | null
  bank_booking_date: string | null
}

export interface UnmatchedBankTx {
  id: number
  booking_date: string
  amount_eur: number
  description: string
  category_id: string | null
}

export interface InvoicePaymentStatus {
  invoice_number: string
  status: string
  gross_total: number
  total_paid: number
  balance: number
}

export interface ReconciliationData {
  year: number
  month: number
  provider_matches: ProviderInvoiceMatch[]
  matched_count: number
  unmatched_count: number
  unmatched_bank_transactions: UnmatchedBankTx[]
  invoice_status: InvoicePaymentStatus | null
}

// ── Working Days ───────────────────────────────────────────────

export interface WorkingDaysResponse {
  year: number
  month: number
  working_days: number
  holidays: string[]
}
