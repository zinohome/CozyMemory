/** Shared response types matching the CozyMemory REST API. */

export interface ConversationMemory {
  id: string;
  user_id: string;
  content: string;
  score?: number | null;
  metadata?: Record<string, unknown> | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ConversationMemoryListResponse {
  success: boolean;
  data: ConversationMemory[];
  total: number;
  message?: string;
  short_term_memories?: ConversationMemory[];
  long_term_memories?: ConversationMemory[];
}

export interface ProfileItem {
  id: string;
  content: string;
  attributes: {
    topic: string;
    sub_topic: string;
  };
}

export interface ProfileResponse {
  success: boolean;
  data: { profiles: ProfileItem[] };
}

export interface ProfileContextResponse {
  success: boolean;
  data: { context: string };
}

export interface DatasetInfo {
  id: string;
  name: string;
}

export interface DatasetListResponse {
  success: boolean;
  data: DatasetInfo[];
  message?: string;
}

export interface AddKnowledgeResponse {
  success: boolean;
  data_id?: string;
  dataset?: string;
  message?: string;
}

export interface CognifyResponse {
  success: boolean;
  pipeline_run_id?: string;
  status?: string;
  message?: string;
}

export interface KnowledgeSearchResult {
  content: string;
  score?: number;
  metadata?: Record<string, unknown>;
}

export interface KnowledgeSearchResponse {
  success: boolean;
  data: KnowledgeSearchResult[];
  message?: string;
}

export interface UnifiedContextResponse {
  success: boolean;
  conversations: ConversationMemory[];
  profile_context: string;
  knowledge: KnowledgeSearchResult[];
  errors?: Record<string, string>;
}

export interface HealthResponse {
  status: string;
  engines: Record<string, { status: string; latency_ms: number }>;
}

export interface DeleteResponse {
  success: boolean;
  message?: string;
}

export interface InsertResponse {
  success: boolean;
  message?: string;
}
