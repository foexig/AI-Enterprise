export interface CurrentUser {
  id: number;
  email: string;
  name: string;
  is_active: boolean;
  is_admin: boolean;
  roles: string[];
  created_at: string;
}

export interface Agent {
  id: number;
  name: string;
  slug: string;
  description: string;
}

export interface ChatSession {
  id: number;
  agent_id: number;
  created_at: string;
  last_activity_at: string;
  expires_at: string;
}

export interface ChatMessage {
  id: number;
  session_id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface MessageSendResponse {
  message: ChatMessage;
  input_tokens: number;
  output_tokens: number;
  model_id: string;
}

// --- Admin ---
export interface AdminUser {
  id: number;
  email: string;
  name: string;
  is_active: boolean;
  is_admin: boolean;
  roles: string[];
  created_at: string;
}

export interface AdminRole {
  id: number;
  name: string;
  user_count: number;
  agent_count: number;
}

export interface AdminAgent {
  id: number;
  name: string;
  slug: string;
  description: string;
  system_prompt: string;
  model_id: string;
  is_active: boolean;
  roles: string[];
  created_at: string;
  updated_at: string;
}
