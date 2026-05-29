// ═══════════════════════════════════════════════════════════════
// ADMIN DASHBOARD — Shared Type Definitions
// ═══════════════════════════════════════════════════════════════

export interface UserRow {
  id: string;
  email: string;
  role: string | null;
  is_active: boolean;
  created_at: string;
  conversation_count: number;
  message_count: number;
  total_tokens: number;
  total_cost: number;
  last_active: string | null;
}

export interface UsageDay {
  date: string;
  tokens: number;
  cost: number;
  requests: number;
  avg_latency_ms?: number;
}

export interface ModelItem {
  provider: string;
  model: string;
  tokens: number;
  cost: number;
  requests: number;
  avg_latency_ms?: number;
}

export interface ProviderItem {
  provider: string;
  tokens: number;
  cost: number;
  requests: number;
}

export interface AuditItem {
  id: string;
  user_id: string | null;
  event_type: string;
  status: string;
  provider_name: string | null;
  model_name: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number | null;
  created_at: string;
}

export interface SecurityItem {
  id: string;
  user_id: string | null;
  event_type: string;
  severity: string;
  status: string;
  ip_address: string | null;
  created_at: string;
}

export interface DlpEventItem {
  id: string;
  user_id: string | null;
  action: string;
  match_count: number;
  redacted_excerpt: string | null;
  created_at: string;
}

export interface GrowthPoint {
  date: string;
  count: number;
}

export interface DashboardData {
  overview: {
    total_users: number;
    active_users: number;
    total_conversations: number;
    total_messages: number;
    total_tokens: number;
    total_cost: number;
    total_requests: number;
    total_organizations: number;
    failed_requests: number;
  };
  today: {
    conversations: number;
    messages: number;
    tokens: number;
    new_users: number;
    errors: number;
  };
  auth: {
    recent_signups_7d: number;
    failed_logins_7d: number;
    total_users: number;
    active_users: number;
  };
  health: {
    database: string;
    total_organizations: number;
    total_requests: number;
  };
  growth: {
    signups_30d: GrowthPoint[];
    conversations_30d: GrowthPoint[];
  };
  users: UserRow[];
  usage_over_time: UsageDay[];
  model_breakdown: ModelItem[];
  provider_breakdown: ProviderItem[];
  recent_audit: AuditItem[];
  recent_security: SecurityItem[];
  dlp: {
    events: DlpEventItem[];
    total: number;
    blocked: number;
  };
}

export interface UserDetailData {
  user: {
    id: string;
    email: string;
    role: string | null;
    is_active: boolean;
    created_at: string;
    organization_id: string | null;
  };
  stats: {
    total_conversations: number;
    total_tokens: number;
    total_cost: number;
    total_requests: number;
  };
  conversations: {
    items: Array<{
      id: string;
      title: string;
      created_at: string;
      updated_at: string;
      message_count: number;
    }>;
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
  };
  usage_history: Array<{
    date: string;
    tokens: number;
    cost: number;
    requests: number;
  }>;
  model_usage: Array<{
    provider: string;
    model: string;
    tokens: number;
    cost: number;
    requests: number;
  }>;
  recent_audit: AuditItem[];
}

export interface ConversationRow {
  id: string;
  title: string;
  user_id: string;
  user_email: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationsResponse {
  items: ConversationRow[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ConversationDetailResponse {
  conversation: {
    id: string;
    title: string;
    user_id: string;
    user_email: string | null;
    created_at: string;
    updated_at: string;
  };
  messages: Array<{
    id: string;
    role: string;
    content: string;
    model_used: string | null;
    provider_used: string | null;
    created_at: string;
  }>;
}

// ═══════════════════════════════════════════════════════════════
// PAGINATED RESPONSES FOR AUDIT / SECURITY / DLP
// ═══════════════════════════════════════════════════════════════

export interface AuditLogsResponse {
  items: AuditItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  event_types: string[];
}

export interface SecurityEventsResponse {
  items: SecurityItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  severity_distribution: Array<{ severity: string; count: number }>;
}

export interface DlpEventsResponse {
  items: DlpEventItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  action_distribution: Array<{ action: string; count: number }>;
}
