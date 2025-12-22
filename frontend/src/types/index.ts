// User Types
export interface User {
  id: string;
  github_id: string;
  username: string;
  email: string;
  avatar_url?: string;
  created_at: string;
}

// Repository Types
export interface Repository {
  _id: string;
  github_repo_id: string;
  name: string;
  full_name: string;
  owner: string;
  owner_id: string;
  installation_id?: number | null;
  is_active: boolean;
  last_commit_sha?: string | null;
  last_pom_change?: string | null;
  created_at: string;
  updated_at: string;
}

// Change Types
export interface Change {
  _id: string;
  repository_id: string;
  commit_sha: string;
  commit_message: string;
  status: 'pending' | 'cloning' | 'preparing' | 'analyzing' | 'fixing' | 'validating' | 'fixed' | 'failed';
  progress: number;
  status_message?: string;
  breaking_changes?: string | null;
  suggested_fix?: string | null;
  diff?: string | null;
  error_message?: string | null;
  pr_url?: string | null;
  pull_request_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BreakingChange {
  dependency: string;
  old_version: string;
  new_version: string;
  affected_files: string[];
  issues: string[];
}

export interface Fix {
  file: string;
  line_number: number;
  old_code: string;
  new_code: string;
  description: string;
}
