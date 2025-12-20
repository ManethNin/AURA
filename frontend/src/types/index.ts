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
  id: string;
  name: string;
  full_name: string;
  owner: string;
  github_id: string;
  url: string;
  private: boolean;
  created_at: string;
  updated_at: string;
}

// Change Types
export interface Change {
  id: string;
  repository_id: string;
  commit_sha: string;
  commit_message: string;
  author: string;
  status: 'pending' | 'analyzed' | 'fixed' | 'pr_created' | 'failed';
  breaking_changes?: BreakingChange[];
  fixes?: Fix[];
  pr_url?: string;
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
