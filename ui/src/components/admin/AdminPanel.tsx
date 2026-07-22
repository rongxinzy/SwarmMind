"use client"

import { useCallback, useEffect, useState } from "react"
import {
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Plus,
  RefreshCcw,
  Shield,
  Trash2,
  Users,
} from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { apiFetch, apiFetchJson } from "@/lib/api"
import { ProvidersPanel } from "./ProvidersPanel"

type AdminTab = "providers" | "organizations" | "users"

type UserRole = "admin" | "member"
type UserStatus = "active" | "disabled"
type TeamRole = "admin" | "member"
type TeamMembershipStatus = "active" | "disabled"
type OrgStatus = "active" | "archived"
type TeamStatus = "active" | "archived"
type ResourceType = "model" | "mcp"

interface User {
  user_id: string
  email: string
  username: string | null
  display_name: string | null
  role: UserRole
  status: UserStatus
  created_at: string
  updated_at: string
  last_login_at: string | null
}

interface UserListResponse {
  items: User[]
  total: number
}

interface Organization {
  organization_id: string
  name: string
  owner_user_id: string
  status: OrgStatus
  created_at: string
  updated_at: string
}

interface OrganizationListResponse {
  items: Organization[]
  total: number
}

interface Team {
  team_id: string
  organization_id: string
  name: string
  status: TeamStatus
  created_at: string
  updated_at: string
}

interface TeamListResponse {
  items: Team[]
  total: number
}

interface TeamMembership {
  membership_id: string
  team_id: string
  user_id: string
  role: TeamRole
  status: TeamMembershipStatus
  created_at: string
  updated_at: string
}

interface TeamMembershipListResponse {
  items: TeamMembership[]
  total: number
}

interface UserAllocation {
  allocation_id: string
  user_id: string
  resource_type: ResourceType
  resource_name: string
  is_allowed: boolean
  created_at: string
  updated_at: string
}

interface UserAllocationListResponse {
  items: UserAllocation[]
  total: number
}

function asTeamRole(value: string): TeamRole {
  if (value !== "admin" && value !== "member") {
    throw new Error(`Invalid team role: ${value}`)
  }
  return value
}

function asUserRole(value: string): UserRole {
  if (value !== "admin" && value !== "member") {
    throw new Error(`Invalid user role: ${value}`)
  }
  return value
}

function asResourceType(value: string): ResourceType {
  if (value !== "model" && value !== "mcp") {
    throw new Error(`Invalid resource type: ${value}`)
  }
  return value
}

const TABS: { id: AdminTab; label: string }[] = [
  { id: "providers", label: "Providers" },
  { id: "organizations", label: "Organizations" },
  { id: "users", label: "Users" },
]

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString("zh-CN", {
    month: "short",
    day: "numeric",
  })
}

function resolveUser(identifier: string, users: User[]): User | undefined {
  const trimmed = identifier.trim()
  if (!trimmed) return undefined
  if (trimmed.includes("@")) {
    return users.find((user) => user.email.toLowerCase() === trimmed.toLowerCase())
  }
  return users.find((user) => user.user_id === trimmed)
}

function StatusBadge({ status }: { status: string }) {
  const isActive = status === "active"
  return (
    <Badge
      variant="secondary"
      className={
        isActive
          ? "bg-[#e9f8ef] text-[#168a4a]"
          : "bg-[#f4f4f4] text-[#858585]"
      }
    >
      {status}
    </Badge>
  )
}

function TabButton({
  active,
  label,
  onClick,
}: {
  active: boolean
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`relative px-3 py-2 text-sm font-medium transition-colors ${
        active ? "text-[#1a1a1a]" : "text-[#858585] hover:text-[#5d5d5d]"
      }`}
    >
      {label}
      {active && (
        <span className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full bg-[#7256f4]" />
      )}
    </button>
  )
}

function CreateOrganizationDialog({
  open,
  users,
  onOpenChange,
  onCreated,
}: {
  open: boolean
  users: User[]
  onOpenChange: (open: boolean) => void
  onCreated: () => void
}) {
  const [name, setName] = useState("")
  const [ownerIdentifier, setOwnerIdentifier] = useState("")
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (open) {
      setName("")
      setOwnerIdentifier("")
      setIsSaving(false)
    }
  }, [open])

  async function handleSubmit(event: React.SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedName = name.trim()
    const owner = resolveUser(ownerIdentifier, users)
    if (!trimmedName) {
      toast.error("请输入组织名称")
      return
    }
    if (!owner) {
      toast.error("未找到所有者用户")
      return
    }
    setIsSaving(true)
    try {
      await apiFetchJson<Organization>("/organizations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: trimmedName,
          owner_user_id: owner.user_id,
        }),
      })
      toast.success("组织已创建")
      onOpenChange(false)
      onCreated()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "创建失败")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>新建组织</DialogTitle>
            <DialogDescription>创建组织并指定所有者。</DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="org-name">组织名称</Label>
            <Input
              id="org-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Acme Inc."
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="org-owner">所有者（用户邮箱或 ID）</Label>
            <Input
              id="org-owner"
              value={ownerIdentifier}
              onChange={(event) => setOwnerIdentifier(event.target.value)}
              placeholder="admin@example.com"
              required
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSaving}
            >
              取消
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner data-icon="inline-start" /> : <CheckCircle2 data-icon="inline-start" />}
              创建
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function OrganizationsTab() {
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [teams, setTeams] = useState<Record<string, Team[]>>({})
  const [memberships, setMemberships] = useState<Record<string, TeamMembership[]>>({})
  const [expandedOrgs, setExpandedOrgs] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  const [creatingOrgId, setCreatingOrgId] = useState<string | null>(null)
  const [newTeamName, setNewTeamName] = useState("")

  const [addingTeamId, setAddingTeamId] = useState<string | null>(null)
  const [memberIdentifier, setMemberIdentifier] = useState("")
  const [memberRole, setMemberRole] = useState<TeamRole>("member")

  const refresh = useCallback(async () => {
    setIsLoading(true)
    try {
      const [orgList, userList] = await Promise.all([
        apiFetchJson<OrganizationListResponse>("/organizations"),
        apiFetchJson<UserListResponse>("/users"),
      ])
      setOrganizations(orgList.items)
      setUsers(userList.items)

      const teamEntries = await Promise.all(
        orgList.items.map(async (org) => {
          const list = await apiFetchJson<TeamListResponse>(
            `/organizations/${org.organization_id}/teams`,
          )
          return [org.organization_id, list.items] as const
        }),
      )
      const teamMap: Record<string, Team[]> = {}
      const allTeams: Team[] = []
      teamEntries.forEach(([orgId, list]) => {
        teamMap[orgId] = list
        allTeams.push(...list)
      })
      setTeams(teamMap)

      const membershipEntries = await Promise.all(
        allTeams.map(async (team) => {
          const list = await apiFetchJson<TeamMembershipListResponse>(
            `/teams/${team.team_id}/members`,
          )
          return [team.team_id, list.items] as const
        }),
      )
      setMemberships(Object.fromEntries(membershipEntries))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "加载组织失败")
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  function userById(userId: string) {
    return users.find((user) => user.user_id === userId)
  }

  function toggleOrg(orgId: string) {
    setExpandedOrgs((prev) => {
      const next = new Set(prev)
      if (next.has(orgId)) {
        next.delete(orgId)
      } else {
        next.add(orgId)
      }
      return next
    })
  }

  async function archiveOrganization(org: Organization) {
    if (!window.confirm(`归档组织 ${org.name}？`)) return
    try {
      await apiFetchJson<Organization>(`/organizations/${org.organization_id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "archived" }),
      })
      toast.success("组织已归档")
      void refresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "归档失败")
    }
  }

  async function createTeam(orgId: string) {
    const name = newTeamName.trim()
    if (!name) return
    try {
      await apiFetchJson<Team>(`/organizations/${orgId}/teams`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      })
      toast.success("团队已创建")
      setNewTeamName("")
      setCreatingOrgId(null)
      void refresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "创建失败")
    }
  }

  async function archiveTeam(team: Team) {
    if (!window.confirm(`归档团队 ${team.name}？`)) return
    try {
      await apiFetchJson<Team>(`/teams/${team.team_id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "archived" }),
      })
      toast.success("团队已归档")
      void refresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "归档失败")
    }
  }

  async function addMember(teamId: string) {
    const user = resolveUser(memberIdentifier, users)
    if (!user) {
      toast.error("未找到用户")
      return
    }
    try {
      await apiFetchJson<TeamMembership>(`/teams/${teamId}/members`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.user_id, role: memberRole }),
      })
      toast.success("成员已添加")
      setMemberIdentifier("")
      setMemberRole("member")
      setAddingTeamId(null)
      void refresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "添加失败")
    }
  }

  async function updateMemberRole(
    teamId: string,
    membership: TeamMembership,
    role: TeamRole,
  ) {
    try {
      await apiFetchJson<TeamMembership>(
        `/teams/${teamId}/members/${membership.membership_id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role }),
        },
      )
      toast.success("角色已更新")
      void refresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "更新失败")
    }
  }

  async function removeMember(teamId: string, membershipId: string) {
    if (!window.confirm("移除该成员？")) return
    try {
      const res = await apiFetch(`/teams/${teamId}/members/${membershipId}`, {
        method: "DELETE",
      })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      toast.success("成员已移除")
      void refresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "移除失败")
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner className="text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium text-[#1a1a1a]">组织与团队</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void refresh()}>
            <RefreshCcw data-icon="inline-start" />
            刷新
          </Button>
          <Button size="sm" onClick={() => setIsDialogOpen(true)}>
            <Plus data-icon="inline-start" />
            新建组织
          </Button>
        </div>
      </div>

      {organizations.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[#d9d9d9] bg-white px-4 py-12 text-center text-sm text-[#858585]">
          暂无组织
        </div>
      ) : (
        <div className="space-y-3">
          {organizations.map((org) => {
            const owner = userById(org.owner_user_id)
            const isExpanded = expandedOrgs.has(org.organization_id)
            const orgTeams = teams[org.organization_id] ?? []
            return (
              <div
                key={org.organization_id}
                className="overflow-hidden rounded-xl border border-[#e8e8e8] bg-white shadow-[0_10px_30px_rgba(20,20,20,0.025)]"
              >
                <div className="flex items-center justify-between gap-3 px-4 py-3">
                  <button
                    type="button"
                    onClick={() => toggleOrg(org.organization_id)}
                    className="flex min-w-0 flex-1 items-center gap-2 text-left"
                  >
                    {isExpanded ? (
                      <ChevronDown className="size-4 shrink-0 text-[#858585]" />
                    ) : (
                      <ChevronRight className="size-4 shrink-0 text-[#858585]" />
                    )}
                    <Building2 className="size-4 shrink-0 text-[#7256f4]" />
                    <span className="truncate text-sm font-medium text-[#1a1a1a]">
                      {org.name}
                    </span>
                    <StatusBadge status={org.status} />
                  </button>
                  <div className="flex shrink-0 items-center gap-2 text-xs text-[#858585]">
                    <span className="hidden sm:inline">
                      所有者 {owner?.email ?? org.owner_user_id}
                    </span>
                    {org.status === "active" && (
                      <Button
                        variant="ghost"
                        size="xs"
                        className="text-destructive"
                        onClick={() => void archiveOrganization(org)}
                      >
                        <Trash2 data-icon="inline-start" />
                        归档
                      </Button>
                    )}
                  </div>
                </div>

                {isExpanded && (
                  <div className="border-t border-[#f0f0f0] px-4 py-3">
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-xs font-medium text-[#5d5d5d]">Teams</h3>
                      {creatingOrgId === org.organization_id ? (
                        <div className="flex items-center gap-2">
                          <Input
                            value={newTeamName}
                            onChange={(event) => setNewTeamName(event.target.value)}
                            placeholder="团队名称"
                            className="h-7 w-40 text-xs"
                          />
                          <Button size="xs" onClick={() => void createTeam(org.organization_id)}>
                            添加
                          </Button>
                          <Button
                            variant="ghost"
                            size="xs"
                            onClick={() => {
                              setCreatingOrgId(null)
                              setNewTeamName("")
                            }}
                          >
                            取消
                          </Button>
                        </div>
                      ) : (
                        <Button
                          variant="outline"
                          size="xs"
                          onClick={() => setCreatingOrgId(org.organization_id)}
                        >
                          <Plus data-icon="inline-start" />
                          新建团队
                        </Button>
                      )}
                    </div>

                    {orgTeams.length === 0 ? (
                      <p className="text-xs text-[#858585]">该组织下暂无团队</p>
                    ) : (
                      <div className="space-y-3">
                        {orgTeams.map((team) => {
                          const teamMembers = memberships[team.team_id] ?? []
                          return (
                            <div
                              key={team.team_id}
                              className="rounded-lg border border-[#e8e8e8] bg-[#fafafa] p-3"
                            >
                              <div className="mb-2 flex items-center justify-between gap-2">
                                <div className="flex min-w-0 items-center gap-2">
                                  <Users className="size-3.5 shrink-0 text-[#858585]" />
                                  <span className="truncate text-sm font-medium text-[#1a1a1a]">
                                    {team.name}
                                  </span>
                                  <StatusBadge status={team.status} />
                                </div>
                                {team.status === "active" && (
                                  <Button
                                    variant="ghost"
                                    size="xs"
                                    className="text-destructive"
                                    onClick={() => void archiveTeam(team)}
                                  >
                                    归档
                                  </Button>
                                )}
                              </div>

                              <div className="space-y-2">
                                {teamMembers.map((membership) => {
                                  const memberUser = userById(membership.user_id)
                                  return (
                                    <div
                                      key={membership.membership_id}
                                      className="flex items-center justify-between gap-2 rounded-md bg-white px-2.5 py-2"
                                    >
                                      <div className="min-w-0">
                                        <p className="truncate text-xs font-medium text-[#1a1a1a]">
                                          {memberUser?.email ?? membership.user_id}
                                        </p>
                                        <p className="truncate text-[11px] text-[#858585]">
                                          {memberUser?.display_name ?? membership.user_id}
                                        </p>
                                      </div>
                                      <div className="flex shrink-0 items-center gap-2">
                                        <Select
                                          value={membership.role}
                                          onValueChange={(value) => {
                                            if (!value) return
                                            void updateMemberRole(
                                              team.team_id,
                                              membership,
                                              asTeamRole(value),
                                            )
                                          }}
                                        >
                                          <SelectTrigger className="h-6 w-24 text-xs">
                                            <SelectValue />
                                          </SelectTrigger>
                                          <SelectContent>
                                            <SelectGroup>
                                              <SelectItem value="admin">admin</SelectItem>
                                              <SelectItem value="member">member</SelectItem>
                                            </SelectGroup>
                                          </SelectContent>
                                        </Select>
                                        <Button
                                          variant="ghost"
                                          size="icon-xs"
                                          className="text-destructive"
                                          aria-label="移除成员"
                                          onClick={() =>
                                            void removeMember(team.team_id, membership.membership_id)
                                          }
                                        >
                                          <Trash2 className="size-3" />
                                        </Button>
                                      </div>
                                    </div>
                                  )
                                })}

                                {addingTeamId === team.team_id ? (
                                  <div className="flex flex-wrap items-center gap-2 pt-1">
                                    <Input
                                      value={memberIdentifier}
                                      onChange={(event) =>
                                        setMemberIdentifier(event.target.value)
                                      }
                                      placeholder="用户邮箱或 ID"
                                      className="h-7 w-44 text-xs"
                                    />
                                    <Select
                                      value={memberRole}
                                      onValueChange={(value) => {
                                        if (!value) return
                                        setMemberRole(asTeamRole(value))
                                      }}
                                    >
                                      <SelectTrigger className="h-7 w-24 text-xs">
                                        <SelectValue />
                                      </SelectTrigger>
                                      <SelectContent>
                                        <SelectGroup>
                                          <SelectItem value="admin">admin</SelectItem>
                                          <SelectItem value="member">member</SelectItem>
                                        </SelectGroup>
                                      </SelectContent>
                                    </Select>
                                    <Button size="xs" onClick={() => void addMember(team.team_id)}>
                                      添加
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="xs"
                                      onClick={() => {
                                        setAddingTeamId(null)
                                        setMemberIdentifier("")
                                        setMemberRole("member")
                                      }}
                                    >
                                      取消
                                    </Button>
                                  </div>
                                ) : (
                                  <Button
                                    variant="ghost"
                                    size="xs"
                                    onClick={() => setAddingTeamId(team.team_id)}
                                  >
                                    <Plus data-icon="inline-start" />
                                    添加成员
                                  </Button>
                                )}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      <CreateOrganizationDialog
        open={isDialogOpen}
        users={users}
        onOpenChange={setIsDialogOpen}
        onCreated={() => void refresh()}
      />
    </div>
  )
}

function CreateUserDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: () => void
}) {
  const [form, setForm] = useState({
    email: "",
    username: "",
    password: "",
    display_name: "",
    role: "member" as UserRole,
  })
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (open) {
      setForm({ email: "", username: "", password: "", display_name: "", role: "member" })
      setIsSaving(false)
    }
  }, [open])

  async function handleSubmit(event: React.SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSaving(true)
    try {
      await apiFetchJson<User>("/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.email.trim(),
          username: form.username.trim() || null,
          password: form.password,
          display_name: form.display_name.trim() || null,
          role: form.role,
          status: "active",
        }),
      })
      toast.success("用户已创建")
      onOpenChange(false)
      onCreated()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "创建失败")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>新建用户</DialogTitle>
            <DialogDescription>创建本地用户并分配角色。</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="user-email">邮箱</Label>
              <Input
                id="user-email"
                type="email"
                value={form.email}
                onChange={(event) =>
                  setForm((current) => ({ ...current, email: event.target.value }))
                }
                placeholder="user@example.com"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="user-username">用户名</Label>
              <Input
                id="user-username"
                value={form.username}
                onChange={(event) =>
                  setForm((current) => ({ ...current, username: event.target.value }))
                }
                placeholder="username"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="user-password">密码</Label>
              <Input
                id="user-password"
                type="password"
                value={form.password}
                onChange={(event) =>
                  setForm((current) => ({ ...current, password: event.target.value }))
                }
                placeholder="••••••"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="user-display">显示名称</Label>
              <Input
                id="user-display"
                value={form.display_name}
                onChange={(event) =>
                  setForm((current) => ({ ...current, display_name: event.target.value }))
                }
                placeholder="Display Name"
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label>角色</Label>
              <Select
                value={form.role}
                onValueChange={(value) => {
                  if (!value) return
                  setForm((current) => ({ ...current, role: asUserRole(value) }))
                }}
              >
                <SelectTrigger className="h-8 w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="admin">admin</SelectItem>
                    <SelectItem value="member">member</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSaving}
            >
              取消
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner data-icon="inline-start" /> : <CheckCircle2 data-icon="inline-start" />}
              创建
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function UsersTab() {
  const [users, setUsers] = useState<User[]>([])
  const [allocations, setAllocations] = useState<Record<string, UserAllocation[]>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  const [expandedUsers, setExpandedUsers] = useState<Set<string>>(new Set())
  const [newAllocation, setNewAllocation] = useState<{
    userId: string
    resourceType: ResourceType
    resourceName: string
    isAllowed: boolean
  } | null>(null)

  const refresh = useCallback(async () => {
    setIsLoading(true)
    try {
      const userList = await apiFetchJson<UserListResponse>("/users")
      setUsers(userList.items)

      const allocationEntries = await Promise.all(
        userList.items.map(async (user) => {
          const list = await apiFetchJson<UserAllocationListResponse>(
            `/admin/users/${user.user_id}/allocations`,
          )
          return [user.user_id, list.items] as const
        }),
      )
      setAllocations(Object.fromEntries(allocationEntries))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "加载用户失败")
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  function toggleUser(userId: string) {
    setExpandedUsers((prev) => {
      const next = new Set(prev)
      if (next.has(userId)) {
        next.delete(userId)
      } else {
        next.add(userId)
      }
      return next
    })
  }

  async function disableUser(user: User) {
    const action = user.status === "active" ? "禁用" : "启用"
    if (!window.confirm(`确定要${action}用户 ${user.email}？`)) return
    try {
      if (user.status === "active") {
        const res = await apiFetch(`/users/${user.user_id}`, { method: "DELETE" })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
      } else {
        await apiFetchJson<User>(`/users/${user.user_id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: "active" }),
        })
      }
      toast.success(`用户已${action}`)
      void refresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "操作失败")
    }
  }

  async function setAllocation(userId: string, allocation: UserAllocationCreate) {
    try {
      await apiFetchJson<UserAllocation>(`/admin/users/${userId}/allocations`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(allocation),
      })
      toast.success("配额已更新")
      void refresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "更新失败")
    }
  }

  async function deleteAllocation(userId: string, allocation: UserAllocation) {
    if (!window.confirm(`删除 ${allocation.resource_type}:${allocation.resource_name}？`)) return
    try {
      const params = new URLSearchParams({
        resource_type: allocation.resource_type,
        resource_name: allocation.resource_name,
      })
      const res = await apiFetch(`/admin/users/${userId}/allocations?${params}`, {
        method: "DELETE",
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      toast.success("配额已删除")
      void refresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "删除失败")
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner className="text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium text-[#1a1a1a]">用户管理</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void refresh()}>
            <RefreshCcw data-icon="inline-start" />
            刷新
          </Button>
          <Button size="sm" onClick={() => setIsDialogOpen(true)}>
            <Plus data-icon="inline-start" />
            新建用户
          </Button>
        </div>
      </div>

      {users.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[#d9d9d9] bg-white px-4 py-12 text-center text-sm text-[#858585]">
          暂无用户
        </div>
      ) : (
        <div className="space-y-3">
          {users.map((user) => {
            const isExpanded = expandedUsers.has(user.user_id)
            const userAllocations = allocations[user.user_id] ?? []
            return (
              <div
                key={user.user_id}
                className="overflow-hidden rounded-xl border border-[#e8e8e8] bg-white shadow-[0_10px_30px_rgba(20,20,20,0.025)]"
              >
                <div className="flex items-center justify-between gap-3 px-4 py-3">
                  <button
                    type="button"
                    onClick={() => toggleUser(user.user_id)}
                    className="flex min-w-0 flex-1 items-center gap-2 text-left"
                  >
                    {isExpanded ? (
                      <ChevronDown className="size-4 shrink-0 text-[#858585]" />
                    ) : (
                      <ChevronRight className="size-4 shrink-0 text-[#858585]" />
                    )}
                    <Shield className="size-4 shrink-0 text-[#7256f4]" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-medium text-[#1a1a1a]">
                          {user.display_name ?? user.username ?? user.email}
                        </span>
                        <StatusBadge status={user.status} />
                        <Badge variant="secondary" className="bg-[#f4f2ff] text-[#7256f4]">
                          {user.role}
                        </Badge>
                      </div>
                      <p className="truncate text-xs text-[#858585]">{user.email}</p>
                    </div>
                  </button>
                  <Button
                    variant={user.status === "active" ? "outline" : "secondary"}
                    size="xs"
                    onClick={() => void disableUser(user)}
                  >
                    {user.status === "active" ? "禁用" : "启用"}
                  </Button>
                </div>

                {isExpanded && (
                  <div className="border-t border-[#f0f0f0] px-4 py-3">
                    <div className="mb-3 grid gap-2 text-xs text-[#5d5d5d] sm:grid-cols-3">
                      <div>
                        <span className="text-[#858585]">用户名</span>
                        <p className="font-medium">{user.username ?? "-"}</p>
                      </div>
                      <div>
                        <span className="text-[#858585]">创建时间</span>
                        <p className="font-medium">{formatDate(user.created_at)}</p>
                      </div>
                      <div>
                        <span className="text-[#858585]">最后登录</span>
                        <p className="font-medium">
                          {user.last_login_at ? formatDate(user.last_login_at) : "-"}
                        </p>
                      </div>
                    </div>

                    <div className="mb-2 flex items-center justify-between">
                      <h3 className="text-xs font-medium text-[#5d5d5d]">资源配额</h3>
                      {newAllocation?.userId === user.user_id ? (
                        <div className="flex flex-wrap items-center gap-2">
                          <Select
                            value={newAllocation.resourceType}
                            onValueChange={(value) => {
                              if (!value) return
                              setNewAllocation((current) =>
                                current
                                  ? { ...current, resourceType: asResourceType(value) }
                                  : current,
                              )
                            }}
                          >
                            <SelectTrigger className="h-7 w-24 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectGroup>
                                <SelectItem value="model">model</SelectItem>
                                <SelectItem value="mcp">mcp</SelectItem>
                              </SelectGroup>
                            </SelectContent>
                          </Select>
                          <Input
                            value={newAllocation.resourceName}
                            onChange={(event) =>
                              setNewAllocation((current) =>
                                current
                                  ? { ...current, resourceName: event.target.value }
                                  : current,
                              )
                            }
                            placeholder="资源名称"
                            className="h-7 w-40 text-xs"
                          />
                          <label className="flex items-center gap-1.5 text-xs">
                            <Switch
                              size="sm"
                              checked={newAllocation.isAllowed}
                              onCheckedChange={(checked) =>
                                setNewAllocation((current) =>
                                  current ? { ...current, isAllowed: checked } : current,
                                )
                              }
                            />
                            允许
                          </label>
                          <Button
                            size="xs"
                            onClick={() =>
                              void setAllocation(user.user_id, {
                                resource_type: newAllocation.resourceType,
                                resource_name: newAllocation.resourceName,
                                is_allowed: newAllocation.isAllowed,
                              })
                            }
                          >
                            保存
                          </Button>
                          <Button
                            variant="ghost"
                            size="xs"
                            onClick={() => setNewAllocation(null)}
                          >
                            取消
                          </Button>
                        </div>
                      ) : (
                        <Button
                          variant="outline"
                          size="xs"
                          onClick={() =>
                            setNewAllocation({
                              userId: user.user_id,
                              resourceType: "model",
                              resourceName: "",
                              isAllowed: true,
                            })
                          }
                        >
                          <Plus data-icon="inline-start" />
                          添加配额
                        </Button>
                      )}
                    </div>

                    {userAllocations.length === 0 ? (
                      <p className="text-xs text-[#858585]">暂无配额</p>
                    ) : (
                      <div className="space-y-2">
                        {userAllocations.map((allocation) => (
                          <div
                            key={allocation.allocation_id}
                            className="flex items-center justify-between gap-2 rounded-md bg-[#fafafa] px-2.5 py-2"
                          >
                            <div className="flex items-center gap-2 text-sm text-[#1a1a1a]">
                              <Badge variant="secondary" className="bg-[#f4f4f4] text-[#5d5d5d]">
                                {allocation.resource_type}
                              </Badge>
                              <span>{allocation.resource_name}</span>
                            </div>
                            <div className="flex items-center gap-3">
                              <label className="flex items-center gap-1.5 text-xs text-[#5d5d5d]">
                                <Switch
                                  size="sm"
                                  checked={allocation.is_allowed}
                                  onCheckedChange={(checked) =>
                                    void setAllocation(user.user_id, {
                                      resource_type: allocation.resource_type,
                                      resource_name: allocation.resource_name,
                                      is_allowed: checked,
                                    })
                                  }
                                />
                                允许
                              </label>
                              <Button
                                variant="ghost"
                                size="icon-xs"
                                className="text-destructive"
                                aria-label="删除配额"
                                onClick={() => void deleteAllocation(user.user_id, allocation)}
                              >
                                <Trash2 className="size-3" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      <CreateUserDialog
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
        onCreated={() => void refresh()}
      />
    </div>
  )
}

interface UserAllocationCreate {
  resource_type: ResourceType
  resource_name: string
  is_allowed: boolean
}

export function AdminPanel() {
  const [activeTab, setActiveTab] = useState<AdminTab>("providers")

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-[#fbfbfa]">
      <div className="border-b border-[#ececea] bg-[#fbfbfa] px-4 py-4 sm:px-6 md:py-5">
        <div className="mb-3 flex items-center gap-2">
          <Shield className="size-5 text-[#7256f4]" />
          <span className="text-xs font-medium text-[#858585]">Admin</span>
        </div>
        <h1 className="text-[32px] font-medium leading-9 text-[#141414]">系统管理</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[#666]">
          管理供应商、组织团队和用户的资源配额。
        </p>
        <div className="mt-4 flex gap-1">
          {TABS.map((tab) => (
            <TabButton
              key={tab.id}
              active={activeTab === tab.id}
              label={tab.label}
              onClick={() => setActiveTab(tab.id)}
            />
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-hidden">
        {activeTab === "providers" && <ProvidersPanel />}
        {activeTab === "organizations" && (
          <div className="h-full overflow-auto px-4 pb-6 pt-4 sm:px-6">
            <OrganizationsTab />
          </div>
        )}
        {activeTab === "users" && (
          <div className="h-full overflow-auto px-4 pb-6 pt-4 sm:px-6">
            <UsersTab />
          </div>
        )}
      </div>
    </div>
  )
}
