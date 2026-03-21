import { useState, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import CapsuleTabs from "@/components/ui/capsule-tabs"

const API = "http://127.0.0.1:8000"

interface ActionProposal {
  id: string
  agent_id: string
  description: string
  target_resource: string | null
  confidence: number
  status: string
  created_at: string
}

interface StrategyEntry {
  situation_tag: string
  agent_id: string
  success_count: number
  failure_count: number
}

// ---- API helpers ----

async function fetchPending(): Promise<{ items: ActionProposal[]; total: number }> {
  const r = await fetch(`${API}/pending`)
  if (!r.ok) throw new Error("Failed to fetch pending")
  return r.json()
}

async function fetchStrategy(): Promise<{ entries: StrategyEntry[] }> {
  const r = await fetch(`${API}/strategy`)
  if (!r.ok) throw new Error("Failed to fetch strategy")
  return r.json()
}

async function approveProposal(id: string) {
  const r = await fetch(`${API}/approve/${id}`, { method: "POST" })
  if (!r.ok) throw new Error("Failed to approve")
  return r.json()
}

async function rejectProposal(id: string) {
  const r = await fetch(`${API}/reject/${id}`, { method: "POST" })
  if (!r.ok) throw new Error("Failed to reject")
  return r.json()
}

async function submitGoal(goal: string) {
  const r = await fetch(`${API}/dispatch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal }),
  })
  if (!r.ok) throw new Error("Failed to dispatch")
  return r.json()
}

async function fetchStatus(goal: string): Promise<{ summary: string }> {
  const r = await fetch(`${API}/status?goal=${encodeURIComponent(goal)}`)
  if (!r.ok) throw new Error("Failed to fetch status")
  return r.json()
}

// ---- Sub-components ----

function ProposalItem({
  proposal,
  onApprove,
  onReject,
}: {
  proposal: ActionProposal
  onApprove: (id: string) => void
  onReject: (id: string) => void
}) {
  const pct = Math.round(proposal.confidence * 100)
  const level = pct >= 70 ? "high" : pct >= 40 ? "mid" : "low"

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline">{proposal.agent_id}</Badge>
            <Badge
              variant={
                level === "high" ? "secondary" : level === "mid" ? "outline" : "destructive"
              }
            >
              {pct}%
            </Badge>
          </div>
          <span className="text-xs text-muted-foreground">
            {new Date(proposal.created_at).toLocaleString()}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-foreground leading-relaxed mb-3">
          {proposal.description}
        </p>
        {proposal.target_resource && (
          <p className="text-xs text-muted-foreground font-mono mb-3">
            {proposal.target_resource}
          </p>
        )}
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground"></span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onApprove(proposal.id)}
            >
              Approve
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => onReject(proposal.id)}
            >
              Reject
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function PendingList({
  proposals,
  onApprove,
  onReject,
  loading,
}: {
  proposals: ActionProposal[]
  onApprove: (id: string) => void
  onReject: (id: string) => void
  loading: boolean
}) {
  if (loading && proposals.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-12 text-center">
        Loading...
      </p>
    )
  }
  if (proposals.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-sm text-muted-foreground">No pending proposals.</p>
          <p className="text-xs text-muted-foreground mt-1">
            Submit a goal above to get started.
          </p>
        </CardContent>
      </Card>
    )
  }
  return (
    <div className="flex flex-col gap-3">
      {proposals.map((p) => (
        <ProposalItem key={p.id} proposal={p} onApprove={onApprove} onReject={onReject} />
      ))}
    </div>
  )
}

function StrategyTable({ entries }: { entries: StrategyEntry[] }) {
  return (
    <Card>
      <CardContent className="p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-4 py-3 text-left text-xs font-medium text-foreground">
                Situation
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-foreground">
                Agent
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-foreground">
                Success
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-foreground">
                Failure
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-foreground">
                Rate
              </th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => {
              const total = e.success_count + e.failure_count
              const rate = total > 0 ? Math.round((e.success_count / total) * 100) : 0
              return (
                <tr key={e.situation_tag} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                    {e.situation_tag}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="outline">{e.agent_id}</Badge>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs text-foreground">
                    {e.success_count}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs text-muted-foreground">
                    {e.failure_count}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs font-medium text-foreground">
                    {total > 0 ? `${rate}%` : "—"}
                  </td>
                </tr>
              )
            })}
            {entries.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground text-sm">
                  No routing rules yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}

// ---- Main App ----

export default function App() {
  const [proposals, setProposals] = useState<ActionProposal[]>([])
  const [strategy, setStrategy] = useState<StrategyEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [goal, setGoal] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [statusGoal, setStatusGoal] = useState("")
  const [statusSummary, setStatusSummary] = useState("")
  const [statusLoading, setStatusLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadPending = useCallback(async () => {
    try {
      const data = await fetchPending()
      setProposals(data.items)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connection error")
    }
  }, [])

  const loadStrategy = useCallback(async () => {
    try {
      const data = await fetchStrategy()
      setStrategy(data.entries)
    } catch (e) {
      console.error(e)
    }
  }, [])

  useEffect(() => {
    loadPending()
    loadStrategy()
    const interval = setInterval(loadPending, 5000)
    return () => clearInterval(interval)
  }, [loadPending, loadStrategy])

  async function handleApprove(id: string) {
    setLoading(true)
    try {
      await approveProposal(id)
      await loadPending()
    } catch (e) {
      alert("Failed: " + (e instanceof Error ? e.message : e))
    } finally {
      setLoading(false)
    }
  }

  async function handleReject(id: string) {
    setLoading(true)
    try {
      await rejectProposal(id)
      await loadPending()
    } catch (e) {
      alert("Failed: " + (e instanceof Error ? e.message : e))
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!goal.trim()) return
    setSubmitting(true)
    try {
      await submitGoal(goal.trim())
      setGoal("")
      await loadPending()
    } catch (e) {
      alert("Failed: " + (e instanceof Error ? e.message : e))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleStatus(e: React.FormEvent) {
    e.preventDefault()
    if (!statusGoal.trim()) return
    setStatusLoading(true)
    setStatusSummary("")
    try {
      const data = await fetchStatus(statusGoal.trim())
      setStatusSummary(data.summary)
    } catch (e) {
      setStatusSummary("Error: " + (e instanceof Error ? e.message : e))
    } finally {
      setStatusLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-sm font-semibold">SwarmMind</h1>
            <p className="text-xs text-muted-foreground">Supervisor</p>
          </div>
          <a
            href="https://github.com/rongxinzy/SwarmMind"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            GitHub
          </a>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8 max-w-3xl">
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Submit a Goal</CardTitle>
            <CardDescription>
              Describe what you want the agent team to do.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                placeholder="e.g. Review the PR for the new payment API..."
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
              />
              <Button type="submit" disabled={submitting || !goal.trim()}>
                {submitting ? "..." : "Submit"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <CapsuleTabs
          items={[
            {
              value: "proposals",
              label: "Pending",
              content: (
                <>
                  {error && (
                    <div className="mb-4 p-3 rounded-lg border border-destructive/30 bg-destructive/10 text-destructive text-sm">
                      {error}
                    </div>
                  )}
                  <PendingList
                    proposals={proposals}
                    onApprove={handleApprove}
                    onReject={handleReject}
                    loading={loading}
                  />
                </>
              ),
            },
            {
              value: "strategy",
              label: "Strategy",
              content: <StrategyTable entries={strategy} />,
            },
            {
              value: "status",
              label: "Status",
              content: (
                <Card>
                  <CardHeader>
                    <CardTitle>LLM Status Renderer</CardTitle>
                    <CardDescription>
                      Ask about any goal. The LLM reads shared context and generates a real-time summary.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <form onSubmit={handleStatus} className="flex gap-2">
                      <Input
                        placeholder="e.g. What is the status of the Q3 financial report?"
                        value={statusGoal}
                        onChange={(e) => setStatusGoal(e.target.value)}
                      />
                      <Button
                        type="submit"
                        variant="outline"
                        disabled={statusLoading || !statusGoal.trim()}
                      >
                        {statusLoading ? "..." : "Render"}
                      </Button>
                    </form>
                    {statusSummary && (
                      <div className="rounded-lg border p-4 text-sm bg-muted/30">
                        {statusSummary}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ),
            },
          ]}
          defaultValue="proposals"
        />
      </main>
    </div>
  )
}
