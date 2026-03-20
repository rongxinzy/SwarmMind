import { useState, useEffect, useCallback } from "react"

const API = "/api"

type ProposalStatus = "pending" | "approved" | "rejected" | "executed"

interface ActionProposal {
  id: string
  agent_id: string
  description: string
  target_resource: string | null
  confidence: number
  status: ProposalStatus
  created_at: string
}

interface StrategyEntry {
  situation_tag: string
  agent_id: string
  success_count: number
  failure_count: number
}

// ---- Components ----

function Badge({ children, variant = "default" }: { children: React.ReactNode; variant?: "default" | "success" | "warning" | "destructive" | "outline" }) {
  const base = "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
  const variants: Record<string, string> = {
    default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
    success: "border-transparent bg-green-100 text-green-800",
    warning: "border-transparent bg-yellow-100 text-yellow-800",
    destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
    outline: "text-foreground",
  }
  return <span className={`${base} ${variants[variant]}`}>{children}</span>
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-lg border bg-card text-card-foreground shadow-sm ${className}`}>
      {children}
    </div>
  )
}

function CardHeader({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-col space-y-1.5 p-6">{children}</div>
}

function CardTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-lg font-semibold leading-none tracking-tight">{children}</h3>
}

function CardDescription({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>
}

function CardContent({ children }: { children: React.ReactNode }) {
  return <div className="p-6 pt-0">{children}</div>
}

function Button({ children, variant = "default", size = "default", onClick, disabled, className = "" }: {
  children: React.ReactNode
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link"
  size?: "default" | "sm" | "lg" | "icon"
  onClick?: () => void
  disabled?: boolean
  className?: string
}) {
  const base = "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
  const variants: Record<string, string> = {
    default: "bg-primary text-primary-foreground hover:bg-primary/90",
    destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
    outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
    secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
    ghost: "hover:bg-accent hover:text-accent-foreground",
    link: "text-primary underline-offset-4 hover:underline",
  }
  const sizes: Record<string, string> = {
    default: "h-9 px-4 py-2",
    sm: "h-8 rounded-md px-3 text-xs",
    lg: "h-10 rounded-md px-8",
    icon: "h-9 w-9",
  }
  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  )
}

function Input({ placeholder, value, onChange, className = "" }: {
  placeholder?: string
  value?: string
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
  className?: string
}) {
  return (
    <input
      type="text"
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      className={`flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
    />
  )
}

function Textarea({ placeholder, value, onChange, className = "" }: {
  placeholder?: string
  value?: string
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  className?: string
}) {
  return (
    <textarea
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      className={`flex min-h-[60px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
    />
  )
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

function PendingList({ proposals, onApprove, onReject, loading }: {
  proposals: ActionProposal[]
  onApprove: (id: string) => void
  onReject: (id: string) => void
  loading: boolean
}) {
  return (
    <div className="space-y-3">
      {loading && proposals.length === 0 && (
        <p className="text-sm text-muted-foreground py-4 text-center">Loading...</p>
      )}
      {proposals.length === 0 && !loading && (
        <p className="text-sm text-muted-foreground py-4 text-center">No pending proposals. All clear.</p>
      )}
      {proposals.map((p) => (
        <Card key={p.id} className="p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Badge variant="outline">{p.agent_id}</Badge>
                <Badge variant={p.confidence > 0.7 ? "success" : p.confidence > 0.4 ? "warning" : "destructive"}>
                  {Math.round(p.confidence * 100)}% confident
                </Badge>
              </div>
              <p className="text-sm text-foreground">{p.description}</p>
              {p.target_resource && (
                <p className="text-xs text-muted-foreground mt-1">Target: {p.target_resource}</p>
              )}
              <p className="text-xs text-muted-foreground mt-1">
                {new Date(p.created_at).toLocaleTimeString()}
              </p>
            </div>
            <div className="flex gap-2 shrink-0">
              <Button variant="default" size="sm" onClick={() => onApprove(p.id)}>
                Approve
              </Button>
              <Button variant="destructive" size="sm" onClick={() => onReject(p.id)}>
                Reject
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}

function StrategyTable({ entries }: { entries: StrategyEntry[] }) {
  return (
    <div className="rounded-md border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-3 py-2 text-left font-medium">Situation</th>
            <th className="px-3 py-2 text-left font-medium">Agent</th>
            <th className="px-3 py-2 text-right font-medium">Success</th>
            <th className="px-3 py-2 text-right font-medium">Failure</th>
            <th className="px-3 py-2 text-right font-medium">Rate</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => {
            const total = e.success_count + e.failure_count
            const rate = total > 0 ? Math.round((e.success_count / total) * 100) : 0
            return (
              <tr key={e.situation_tag} className="border-b last:border-0">
                <td className="px-3 py-2 font-mono text-xs">{e.situation_tag}</td>
                <td className="px-3 py-2">
                  <Badge variant="outline">{e.agent_id}</Badge>
                </td>
                <td className="px-3 py-2 text-right text-green-600">{e.success_count}</td>
                <td className="px-3 py-2 text-right text-red-600">{e.failure_count}</td>
                <td className="px-3 py-2 text-right">
                  <span className={rate >= 80 ? "text-green-600" : rate >= 60 ? "text-yellow-600" : "text-red-600"}>
                    {rate}%
                  </span>
                </td>
              </tr>
            )
          })}
          {entries.length === 0 && (
            <tr>
              <td colSpan={5} className="px-3 py-4 text-center text-muted-foreground">
                No routing rules yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

// ---- Main App ----

type Tab = "proposals" | "strategy" | "status"

export default function App() {
  const [tab, setTab] = useState<Tab>("proposals")
  const [proposals, setProposals] = useState<ActionProposal[]>([])
  const [strategy, setStrategy] = useState<StrategyEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [goal, setGoal] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [statusGoal, setStatusGoal] = useState("")
  const [statusSummary, setStatusSummary] = useState("")
  const [statusLoading, setStatusLoading] = useState(false)
  const [error, setError] = useState<string | null>( null)

  const loadPending = useCallback(async () => {
    try {
      const data = await fetchPending()
      setProposals(data.items)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connection error — is the API running?")
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
      alert("Failed to approve: " + (e instanceof Error ? e.message : e))
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
      alert("Failed to reject: " + (e instanceof Error ? e.message : e))
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmitGoal(e: React.FormEvent) {
    e.preventDefault()
    if (!goal.trim()) return
    setSubmitting(true)
    try {
      await submitGoal(goal.trim())
      setGoal("")
      await loadPending()
      setTab("proposals")
    } catch (e) {
      alert("Failed to submit: " + (e instanceof Error ? e.message : e))
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
      {/* Header */}
      <header className="border-b bg-white">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight">🤖 SwarmMind</h1>
            <p className="text-xs text-muted-foreground">Supervisor Interface</p>
          </div>
          <a
            href="https://github.com/rongxinzy/SwarmMind"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            View on GitHub →
          </a>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 max-w-5xl">
        {/* Submit goal */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Submit a Goal</CardTitle>
            <CardDescription>
              Describe what you want the agent team to do. Be specific.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmitGoal} className="flex gap-2">
              <Input
                placeholder="e.g. 'Review the PR for the new payment API and suggest improvements'"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                className="flex-1"
              />
              <Button type="submit" disabled={submitting || !goal.trim()}>
                {submitting ? "Submitting..." : "Submit Goal"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Tabs */}
        <div className="flex gap-1 border-b mb-6">
          {([
            ["proposals", "Pending Proposals"],
            ["strategy", "Strategy Table"],
            ["status", "Status Renderer"],
          ] as [Tab, string][]).map(([t, label]) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                tab === t
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {label}
              {t === "proposals" && proposals.length > 0 && (
                <span className="ml-2 bg-primary text-primary-foreground rounded-full px-1.5 py-0.5 text-xs">
                  {proposals.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === "proposals" && (
          <>
            {error && (
              <div className="mb-4 p-3 rounded-md bg-destructive/10 text-destructive text-sm">
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
        )}

        {tab === "strategy" && (
          <StrategyTable entries={strategy} />
        )}

        {tab === "status" && (
          <Card>
            <CardHeader>
              <CardTitle>LLM Status Renderer</CardTitle>
              <CardDescription>
                Ask about any goal's status. The LLM reads shared context and generates a real-time summary.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <form onSubmit={handleStatus} className="flex gap-2">
                <Input
                  placeholder="e.g. 'What is the status of the Q3 financial report?'"
                  value={statusGoal}
                  onChange={(e) => setStatusGoal(e.target.value)}
                  className="flex-1"
                />
                <Button type="submit" disabled={statusLoading || !statusGoal.trim()}>
                  {statusLoading ? "Rendering..." : "Render Status"}
                </Button>
              </form>
              {statusSummary && (
                <div className="p-4 rounded-lg bg-muted/50 border text-sm leading-relaxed">
                  {statusSummary}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}
