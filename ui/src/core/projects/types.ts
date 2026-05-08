export interface ProjectAgentTeamInstance {
  instance_id: string;
  project_id: string;
  team_template_id: string;
  team_name: string;
  team_description?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Project {
  project_id: string;
  title: string;
  goal?: string | null;
  scope?: string | null;
  constraints?: string | null;
  source_conversation_id?: string | null;
  conversation_id?: string | null;
  next_step?: string | null;
  phase?: string | null;
  risk_level?: string | null;
  status: string;
  agent_team?: ProjectAgentTeamInstance | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
}

export interface Run {
  run_id: string;
  project_id?: string | null;
  conversation_id?: string | null;
  status: string;
  goal?: string | null;
  summary?: string | null;
  started_at: string;
  completed_at?: string | null;
}

export interface Task {
  task_id: string;
  project_id: string;
  run_id?: string | null;
  title: string;
  description?: string | null;
  status: string;
  priority: string;
  created_at: string;
  updated_at: string;
}

export interface Artifact {
  artifact_id: string;
  conversation_id?: string | null;
  project_id?: string | null;
  name?: string | null;
  path?: string | null;
  mime_type?: string | null;
  size_bytes?: number | null;
  artifact_type?: string | null;
  created_at: string;
}

export interface ApprovalRequest {
  approval_id: string;
  project_id: string;
  title: string;
  status: string;
  risk_tier: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectOverviewStats {
  task_count: number;
  artifact_count: number;
  run_count: number;
  blocked_count: number;
  pending_approval_count: number;
}

export interface ProjectOverviewResponse {
  project: Project;
  stats: ProjectOverviewStats;
  recent_tasks: Task[];
  recent_artifacts: Artifact[];
  recent_runs: Run[];
  recent_approvals: ApprovalRequest[];
}
