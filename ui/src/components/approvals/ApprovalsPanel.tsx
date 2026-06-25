import { useEffect, useState } from "react"
import { CheckCircle, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { Spinner } from "@/components/ui/spinner"
import { apiFetch, apiFetchJson } from "@/lib/api"
import { toast } from "sonner"

interface Approval {
  approval_id: string
  run_id: string
  capability: string
  risk_tier: string
  status: string
  requested_at: string
}

export function ApprovalsPanel() {
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [actingId, setActingId] = useState<string | null>(null)

  const fetchApprovals = () => {
    setIsLoading(true)
    apiFetchJson<{ items: Approval[]; total: number }>("/approvals")
      .then((data) => setApprovals(data.items))
      .catch((err: unknown) => toast.error(err instanceof Error ? err.message : "加载审批失败"))
      .finally(() => setIsLoading(false))
  }

  useEffect(() => {
    fetchApprovals()
  }, [])

  async function respond(id: string, action: "approve" | "reject") {
    setActingId(id)
    try {
      const res = await apiFetch(`/approvals/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      toast.success(action === "approve" ? "已批准" : "已拒绝")
      fetchApprovals()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "操作失败")
    } finally {
      setActingId(null)
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Spinner className="text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col overflow-auto p-6">
      <h1 className="mb-4 text-xl font-semibold">审批中心</h1>
      {approvals.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center">
          <Empty className="max-w-md">
            <EmptyHeader>
              <EmptyTitle>暂无审批请求</EmptyTitle>
              <EmptyDescription>所有审批均已处理完毕。</EmptyDescription>
            </EmptyHeader>
          </Empty>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {approvals.map((a) => (
            <Card key={a.approval_id}>
              <CardHeader>
                <CardTitle className="text-base">{a.capability}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-1 text-sm text-muted-foreground">
                  <p>风险等级：{a.risk_tier}</p>
                  <p>状态：{a.status}</p>
                  <p>请求时间：{a.requested_at}</p>
                </div>
                {a.status === "pending" && (
                  <div className="mt-4 flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={actingId === a.approval_id}
                      onClick={() => void respond(a.approval_id, "approve")}
                    >
                      {actingId === a.approval_id ? (
                        <Spinner data-icon="inline-start" />
                      ) : (
                        <CheckCircle data-icon="inline-start" />
                      )}
                      批准
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={actingId === a.approval_id}
                      onClick={() => void respond(a.approval_id, "reject")}
                    >
                      <XCircle data-icon="inline-start" />
                      拒绝
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
