import { useCallback, useEffect, useMemo, useState } from "react"
import type { LucideIcon } from "lucide-react"
import {
  Activity,
  Brain,
  CheckCircle2,
  Copy,
  Cpu,
  Eye,
  Gauge,
  KeyRound,
  Pencil,
  Plus,
  RefreshCcw,
  Route,
  ServerCog,
  ShieldCheck,
  Trash2,
  X,
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
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
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

type LlmProviderType =
  | "openai"
  | "anthropic"
  | "azure_openai"
  | "gemini"
  | "dashscope"
  | "moonshot"
  | "minimax"
  | "deepseek"
  | "vllm"
  | "custom"

interface ProviderModel {
  model_name: string
  litellm_model: string
  display_name?: string | null
  supports_vision: boolean
  supports_thinking: boolean
  fallback_model_names: string[]
  is_enabled?: boolean
}

interface ProviderSummary {
  provider_id: string
  name: string
  provider_type: LlmProviderType
  base_url?: string | null
  is_enabled: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}

interface ProviderDetail extends ProviderSummary {
  models: ProviderModel[]
}

interface ProviderListResponse {
  items: ProviderSummary[]
  total: number
}

interface RuntimeModel {
  name: string
  provider: string
  model: string
  display_name?: string | null
  supports_vision: boolean
  supports_thinking: boolean
  capability_tags: string[]
  is_default: boolean
}

interface RuntimeModelCatalogResponse {
  models: RuntimeModel[]
  default_model?: string | null
}

interface GatewayKeyResponse {
  gateway_key: string
  gateway_base_url: string
}

interface ModelFormRow {
  model_name: string
  litellm_model: string
  display_name: string
  supports_vision: boolean
  supports_thinking: boolean
}

interface ProviderFormState {
  name: string
  provider_type: LlmProviderType
  api_key: string
  base_url: string
  is_default: boolean
  models: ModelFormRow[]
}

const PROVIDER_TYPES: { value: LlmProviderType; label: string }[] = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "dashscope", label: "DashScope" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "moonshot", label: "Moonshot" },
  { value: "minimax", label: "MiniMax" },
  { value: "gemini", label: "Gemini" },
  { value: "azure_openai", label: "Azure OpenAI" },
  { value: "vllm", label: "vLLM" },
  { value: "custom", label: "Custom" },
]

const EMPTY_MODEL: ModelFormRow = {
  model_name: "",
  litellm_model: "",
  display_name: "",
  supports_vision: false,
  supports_thinking: false,
}

const EMPTY_FORM: ProviderFormState = {
  name: "",
  provider_type: "openai",
  api_key: "",
  base_url: "",
  is_default: false,
  models: [{ ...EMPTY_MODEL }],
}

function providerTypeLabel(type: LlmProviderType) {
  return PROVIDER_TYPES.find((item) => item.value === type)?.label ?? type
}

function isProviderType(value: string | null): value is LlmProviderType {
  return PROVIDER_TYPES.some((item) => item.value === value)
}

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString("zh-CN", {
    month: "short",
    day: "numeric",
  })
}

function maskSecret(value?: string | null) {
  if (!value) return "未生成"
  if (value.length <= 10) return "••••••"
  return `${value.slice(0, 4)}••••${value.slice(-4)}`
}

function normalizeModels(rows: ModelFormRow[]): ProviderModel[] {
  return rows
    .map((row) => {
      const modelName = row.model_name.trim()
      const litellmModel = row.litellm_model.trim()
      const name = modelName || litellmModel
      const gatewayName = litellmModel || modelName
      return {
        model_name: name,
        litellm_model: gatewayName,
        display_name: row.display_name.trim() || null,
        supports_vision: row.supports_vision,
        supports_thinking: row.supports_thinking,
        fallback_model_names: [],
        is_enabled: true,
      }
    })
    .filter((model) => model.model_name && model.litellm_model)
}

function toFormState(provider: ProviderDetail | null): ProviderFormState {
  if (!provider) return { ...EMPTY_FORM, models: [{ ...EMPTY_MODEL }] }
  return {
    name: provider.name,
    provider_type: provider.provider_type,
    api_key: "",
    base_url: provider.base_url ?? "",
    is_default: provider.is_default,
    models:
      provider.models.length > 0
        ? provider.models.map((model) => ({
            model_name: model.model_name,
            litellm_model: model.litellm_model,
            display_name: model.display_name ?? "",
            supports_vision: model.supports_vision,
            supports_thinking: model.supports_thinking,
          }))
        : [{ ...EMPTY_MODEL }],
  }
}

function Metric({
  icon: Icon,
  label,
  description,
  value,
  tone,
}: {
  icon: LucideIcon
  label: string
  description: string
  value: string | number
  tone?: "green" | "amber" | "purple"
}) {
  const toneClass =
    tone === "green"
      ? "bg-[#e9f8ef] text-[#168a4a] ring-[#cfeeda]"
      : tone === "amber"
        ? "bg-[#fff6df] text-[#946200] ring-[#f4dfaa]"
        : tone === "purple"
          ? "bg-[#f4f2ff] text-[#7256f4] ring-[#ded8ff]"
          : "bg-[#f4f4f4] text-[#5d5d5d] ring-[#e8e8e8]"

  return (
    <div className="rounded-xl border border-[#e8e8e8] bg-white p-4 shadow-[0_8px_24px_rgba(20,20,20,0.025)]">
      <div className="flex min-w-0 items-center gap-2">
        <span className={`inline-flex size-7 shrink-0 items-center justify-center rounded-lg ring-1 ${toneClass}`}>
          <Icon className="size-3.5" />
        </span>
        <p className="truncate text-xs font-medium text-[#5d5d5d]">{label}</p>
      </div>
      <p className="mt-4 truncate text-2xl font-medium leading-7 text-[#1a1a1a]">{value}</p>
      <p className="mt-2 line-clamp-2 text-xs leading-5 text-[#858585]">{description}</p>
    </div>
  )
}

function GatewayStatusPill({ ready }: { ready: boolean }) {
  return (
    <span
      className={`inline-flex h-7 items-center gap-1.5 rounded-full border px-3 text-xs font-medium ${
        ready
          ? "border-[#d9ebdf] bg-[#f7fbf7] text-[#168a4a]"
          : "border-[#f0dfb8] bg-[#fffaf0] text-[#946200]"
      }`}
    >
      <span className={`size-1.5 rounded-full ${ready ? "bg-[#168a4a]" : "bg-[#946200]"}`} />
      {ready ? "Gateway ready" : "Gateway pending"}
    </span>
  )
}

function CapabilityBadges({ model }: { model: ProviderModel | RuntimeModel }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {model.supports_thinking && (
        <Badge variant="secondary" className="gap-1 bg-[#f4f4f4] text-[#5d5d5d]">
          <Brain className="size-3" />
          deep
        </Badge>
      )}
      {model.supports_vision && (
        <Badge variant="secondary" className="gap-1 bg-[#eef6ff] text-[#3b6ea8]">
          <Eye className="size-3" />
          vision
        </Badge>
      )}
      {!model.supports_thinking && !model.supports_vision && (
        <Badge variant="secondary" className="bg-[#f4f4f4] text-[#5d5d5d]">
          fast
        </Badge>
      )}
    </div>
  )
}

function ProviderFormDialog({
  open,
  provider,
  onOpenChange,
  onSaved,
}: {
  open: boolean
  provider: ProviderDetail | null
  onOpenChange: (open: boolean) => void
  onSaved: () => void
}) {
  const [form, setForm] = useState<ProviderFormState>(() => toFormState(provider))
  const [isSaving, setIsSaving] = useState(false)
  const isEditing = Boolean(provider)

  useEffect(() => {
    if (open) {
      setForm(toFormState(provider))
    }
  }, [open, provider])

  const canSubmit = form.name.trim().length > 0 && (isEditing || form.api_key.trim().length > 0)

  function updateModel(index: number, patch: Partial<ModelFormRow>) {
    setForm((current) => ({
      ...current,
      models: current.models.map((model, itemIndex) =>
        itemIndex === index ? { ...model, ...patch } : model,
      ),
    }))
  }

  function removeModel(index: number) {
    setForm((current) => ({
      ...current,
      models:
        current.models.length === 1
          ? [{ ...EMPTY_MODEL }]
          : current.models.filter((_, itemIndex) => itemIndex !== index),
    }))
  }

  async function handleSubmit(event: React.SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSubmit) return
    setIsSaving(true)
    try {
      const models = normalizeModels(form.models)
      const apiKey = form.api_key.trim()
      const baseUrl = form.base_url.trim()
      if (provider) {
        await apiFetchJson<ProviderDetail>(`/llm-providers/${provider.provider_id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: form.name.trim(),
            ...(apiKey.length > 0 ? { api_key: apiKey } : {}),
            base_url: baseUrl.length > 0 ? baseUrl : null,
            is_default: form.is_default,
            models,
          }),
        })
      } else {
        await apiFetchJson<ProviderDetail>("/llm-providers", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: form.name.trim(),
            provider_type: form.provider_type,
            api_key: apiKey,
            base_url: baseUrl.length > 0 ? baseUrl : null,
            is_default: form.is_default,
            models,
          }),
        })
      }
      toast.success(provider ? "供应商已更新" : "供应商已添加")
      onOpenChange(false)
      onSaved()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "保存失败")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[calc(100vh-2rem)] overflow-y-auto sm:max-w-3xl">
        <form onSubmit={handleSubmit} className="space-y-5">
          <DialogHeader>
            <DialogTitle>{isEditing ? "编辑供应商" : "添加供应商"}</DialogTitle>
            <DialogDescription>
              {isEditing ? "更新账号、模型和默认路由。" : "接入新的 LLM 账号和可路由模型。"}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="provider-name">名称</Label>
              <Input
                id="provider-name"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Production OpenAI"
                required
              />
            </div>
            <div className="space-y-2">
              <Label>类型</Label>
              <Select
                value={form.provider_type}
                onValueChange={(value) => {
                  if (!isProviderType(value)) return
                  setForm((current) => ({
                    ...current,
                    provider_type: value,
                  }))
                }}
                disabled={isEditing}
              >
                <SelectTrigger className="h-8 w-full">
                  <SelectValue placeholder="选择类型" />
                </SelectTrigger>
                <SelectContent align="start">
                  <SelectGroup>
                    {PROVIDER_TYPES.map((item) => (
                      <SelectItem key={item.value} value={item.value}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="provider-key">API Key</Label>
              <Input
                id="provider-key"
                type="password"
                value={form.api_key}
                onChange={(event) => setForm((current) => ({ ...current, api_key: event.target.value }))}
                placeholder={isEditing ? "留空保持不变" : "sk-..."}
                required={!isEditing}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="provider-base-url">Base URL</Label>
              <Input
                id="provider-base-url"
                value={form.base_url}
                onChange={(event) =>
                  setForm((current) => ({ ...current, base_url: event.target.value }))
                }
                placeholder="https://api.openai.com/v1"
              />
            </div>
          </div>

          <div className="flex items-center justify-between rounded-lg border border-[#e8e8e8] bg-[#fafafa] px-3 py-2">
            <div>
              <p className="text-sm font-medium text-[#1a1a1a]">默认供应商</p>
              <p className="mt-1 text-xs text-[#858585]">用于没有显式模型选择的运行。</p>
            </div>
            <Switch
              checked={form.is_default}
              onCheckedChange={(checked) =>
                setForm((current) => ({ ...current, is_default: checked }))
              }
            />
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <Label>模型</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  setForm((current) => ({
                    ...current,
                    models: [...current.models, { ...EMPTY_MODEL }],
                  }))
                }
              >
                <Plus data-icon="inline-start" />
                添加模型
              </Button>
            </div>
            <div className="space-y-2">
              {form.models.map((model, index) => (
                <div key={index} className="rounded-lg border border-[#e8e8e8] bg-white p-3">
                  <div className="grid gap-2 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
                    <Input
                      value={model.model_name}
                      onChange={(event) => updateModel(index, { model_name: event.target.value })}
                      placeholder="模型名"
                    />
                    <Input
                      value={model.litellm_model}
                      onChange={(event) =>
                        updateModel(index, { litellm_model: event.target.value })
                      }
                      placeholder="网关模型名"
                    />
                    <Input
                      value={model.display_name}
                      onChange={(event) => updateModel(index, { display_name: event.target.value })}
                      placeholder="显示名称"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="justify-self-end text-[#858585]"
                      aria-label="移除模型"
                      onClick={() => removeModel(index)}
                    >
                      <X className="size-4" />
                    </Button>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-4 text-sm text-[#5d5d5d]">
                    <label className="flex items-center gap-2">
                      <Switch
                        size="sm"
                        checked={model.supports_thinking}
                        onCheckedChange={(checked) => updateModel(index, { supports_thinking: checked })}
                      />
                      deep
                    </label>
                    <label className="flex items-center gap-2">
                      <Switch
                        size="sm"
                        checked={model.supports_vision}
                        onCheckedChange={(checked) => updateModel(index, { supports_vision: checked })}
                      />
                      vision
                    </label>
                  </div>
                </div>
              ))}
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
            <Button type="submit" disabled={!canSubmit || isSaving}>
              {isSaving ? <Spinner data-icon="inline-start" /> : <CheckCircle2 data-icon="inline-start" />}
              保存
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function ProvidersPanel() {
  const [providers, setProviders] = useState<ProviderDetail[]>([])
  const [runtimeModels, setRuntimeModels] = useState<RuntimeModel[]>([])
  const [gateway, setGateway] = useState<GatewayKeyResponse | null>(null)
  const [selectedProviderId, setSelectedProviderId] = useState<string | null>(null)
  const [editingProvider, setEditingProvider] = useState<ProviderDetail | null>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const selectedProvider = useMemo(
    () => providers.find((provider) => provider.provider_id === selectedProviderId) ?? providers[0] ?? null,
    [providers, selectedProviderId],
  )

  const defaultProvider = useMemo(
    () => providers.find((provider) => provider.is_default) ?? null,
    [providers],
  )

  const refreshAll = useCallback(async () => {
    setIsLoading(true)
    try {
      const [providerList, catalog, gatewayKey] = await Promise.all([
        apiFetchJson<ProviderListResponse>("/llm-providers"),
        apiFetchJson<RuntimeModelCatalogResponse>("/runtime/models"),
        apiFetchJson<GatewayKeyResponse>("/gateway/key"),
      ])
      const details = await Promise.all(
        providerList.items.map((provider) =>
          apiFetchJson<ProviderDetail>(`/llm-providers/${provider.provider_id}`).catch(() => ({
            ...provider,
            models: [],
          })),
        ),
      )
      setProviders(details)
      setRuntimeModels(catalog.models)
      setGateway(gatewayKey)
      setSelectedProviderId((current) => {
        if (current && details.some((provider) => provider.provider_id === current)) return current
        return details[0]?.provider_id ?? null
      })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "加载供应配置失败")
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshAll()
  }, [refreshAll])

  async function copyText(value: string | undefined, label: string) {
    if (!value) return
    await navigator.clipboard.writeText(value)
    toast.success(`${label}已复制`)
  }

  async function deleteProvider(provider: ProviderDetail) {
    if (!window.confirm(`删除 ${provider.name}？`)) return
    const res = await apiFetch(`/llm-providers/${provider.provider_id}`, { method: "DELETE" })
    if (!res.ok) {
      toast.error(`HTTP ${res.status}`)
      return
    }
    toast.success("供应商已删除")
    void refreshAll()
  }

  async function markDefault(provider: ProviderDetail) {
    await apiFetchJson<ProviderDetail>(`/llm-providers/${provider.provider_id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_default: true }),
    })
    toast.success("默认供应商已更新")
    void refreshAll()
  }

  function openCreateDialog() {
    setEditingProvider(null)
    setIsDialogOpen(true)
  }

  function openEditDialog(provider: ProviderDetail) {
    setEditingProvider(provider)
    setIsDialogOpen(true)
  }

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center bg-white">
        <Spinner className="text-muted-foreground" />
      </div>
    )
  }

  const thinkingModels = runtimeModels.filter((model) => model.supports_thinking).length
  const visionModels = runtimeModels.filter((model) => model.supports_vision).length
  const enabledProviders = providers.filter((provider) => provider.is_enabled).length
  const gatewayReady = Boolean(gateway?.gateway_base_url && gateway.gateway_key)

  return (
    <div className="flex flex-1 flex-col overflow-auto bg-[#fbfbfa] px-4 pb-6 pt-14 sm:px-6 md:pt-6">
      <div className="mb-6 flex flex-col gap-4 border-b border-[#ececea] pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <GatewayStatusPill ready={gatewayReady} />
            <span className="inline-flex h-7 max-w-full items-center gap-1.5 truncate rounded-full border border-[#e8e8e8] bg-white px-3 font-mono text-xs text-[#5d5d5d]">
              {gateway?.gateway_base_url ?? "gateway not configured"}
            </span>
          </div>
          <h1 className="text-[32px] font-medium leading-9 text-[#141414]">算力供应</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#666]">
            统一管理供应商账号、模型能力和 DeerFlow Gateway 路由，运行时只暴露可用模型。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" className="rounded-full" onClick={() => void refreshAll()}>
            <RefreshCcw data-icon="inline-start" />
            刷新
          </Button>
          <Button size="sm" className="rounded-full" onClick={openCreateDialog}>
            <Plus data-icon="inline-start" />
            添加供应商
          </Button>
        </div>
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          icon={ServerCog}
          label="供应商"
          description={`${enabledProviders} 个账号处于启用状态`}
          value={providers.length}
          tone={providers.length > 0 ? "green" : "amber"}
        />
        <Metric
          icon={Cpu}
          label="可用模型"
          description="进入 DeerFlow model picker 的模型数量"
          value={runtimeModels.length}
          tone={runtimeModels.length > 0 ? "green" : "amber"}
        />
        <Metric
          icon={Brain}
          label="能力模型"
          description={`${thinkingModels} deep / ${visionModels} vision`}
          value={thinkingModels + visionModels}
          tone="purple"
        />
        <Metric
          icon={Route}
          label="默认路由"
          description={defaultProvider ? providerTypeLabel(defaultProvider.provider_type) : "尚未设置默认供应商"}
          value={defaultProvider?.name ?? "未设置"}
        />
      </div>

      {providers.length === 0 ? (
        <div className="flex min-h-[420px] flex-1 items-center justify-center rounded-xl border border-dashed border-[#d9d9d9] bg-white">
          <Empty className="max-w-md">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <ServerCog />
              </EmptyMedia>
              <EmptyTitle>暂无供应商</EmptyTitle>
              <EmptyDescription>添加一个供应商后，模型会进入运行时选择器。</EmptyDescription>
            </EmptyHeader>
            <Button className="mt-5 rounded-full" onClick={openCreateDialog}>
              <Plus data-icon="inline-start" />
              添加供应商
            </Button>
          </Empty>
        </div>
      ) : (
        <div className="grid flex-1 gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
          <div className="min-w-0 space-y-5">
            <section className="min-w-0 overflow-hidden rounded-xl border border-[#e8e8e8] bg-white shadow-[0_10px_30px_rgba(20,20,20,0.025)]">
              <div className="flex items-center justify-between border-b border-[#eeeeea] px-4 py-3">
                <div className="flex items-center gap-2">
                  <ServerCog className="size-4 text-[#7256f4]" />
                  <h2 className="text-sm font-medium text-[#1a1a1a]">Provider Pool</h2>
                </div>
                <span className="text-xs text-[#858585]">{providers.length} active</span>
              </div>
              <div className="divide-y divide-[#f0f0f0]">
                {providers.map((provider) => {
                  const selected = provider.provider_id === selectedProvider?.provider_id
                  return (
                    <button
                      key={provider.provider_id}
                      type="button"
                      className={`grid w-full gap-3 px-4 py-3 text-left transition-colors md:grid-cols-[minmax(0,1fr)_118px_104px_92px] md:items-center ${
                        selected ? "bg-[#fbfbff] shadow-[inset_3px_0_0_#7256f4]" : "hover:bg-[#fafafa]"
                      }`}
                      onClick={() => setSelectedProviderId(provider.provider_id)}
                    >
                      <div className="min-w-0">
                        <div className="flex min-w-0 items-center gap-2">
                          <span
                            className={`size-1.5 shrink-0 rounded-full ${
                              provider.is_enabled ? "bg-[#168a4a]" : "bg-[#c7c7c7]"
                            }`}
                          />
                          <span className="truncate text-sm font-medium text-[#1a1a1a]">{provider.name}</span>
                        </div>
                        <p className="mt-1 truncate text-xs text-[#858585]">
                          {provider.base_url ?? "default endpoint"}
                        </p>
                      </div>
                      <div className="flex items-center gap-1.5 md:justify-start">
                        <Badge variant="secondary" className="bg-[#f4f4f4] text-[#5d5d5d]">
                          {providerTypeLabel(provider.provider_type)}
                        </Badge>
                      </div>
                      <p className="text-sm text-[#5d5d5d]">{provider.models.length} models</p>
                      <div className="flex items-center gap-1.5">
                        {provider.is_default ? (
                          <Badge variant="secondary" className="bg-[#e9f8ef] text-[#168a4a]">
                            default
                          </Badge>
                        ) : (
                          <span className="text-xs text-[#858585]">standby</span>
                        )}
                      </div>
                    </button>
                  )
                })}
              </div>
            </section>

            <section className="min-w-0 overflow-hidden rounded-xl border border-[#e8e8e8] bg-white shadow-[0_10px_30px_rgba(20,20,20,0.025)]">
              <div className="flex items-center justify-between border-b border-[#eeeeea] px-4 py-3">
                <div className="flex items-center gap-2">
                  <Gauge className="size-4 text-[#7256f4]" />
                  <h2 className="text-sm font-medium text-[#1a1a1a]">Runtime Model Catalog</h2>
                </div>
                <span className="text-xs text-[#858585]">{runtimeModels.length} routed</span>
              </div>
              {runtimeModels.length === 0 ? (
                <div className="px-4 py-8 text-center text-sm text-[#858585]">
                  暂无可路由模型
                </div>
              ) : (
                <div className="divide-y divide-[#f0f0f0]">
                  {runtimeModels.map((model) => (
                    <div
                      key={`${model.provider}-${model.name}`}
                      className="grid gap-3 px-4 py-3 md:grid-cols-[minmax(0,1fr)_128px_140px_84px] md:items-center"
                    >
                      <div className="min-w-0">
                        <div className="flex min-w-0 items-center gap-2">
                          <span className="truncate text-sm font-medium text-[#1a1a1a]">
                            {model.display_name ?? model.name}
                          </span>
                          {model.is_default && (
                            <Badge variant="secondary" className="bg-[#f4f2ff] text-[#7256f4]">
                              default
                            </Badge>
                          )}
                        </div>
                        <p className="mt-1 truncate font-mono text-xs text-[#858585]">{model.model}</p>
                      </div>
                      <p className="truncate text-sm text-[#5d5d5d]">{model.provider}</p>
                      <CapabilityBadges model={model} />
                      <div className="flex items-center gap-1.5 text-xs text-[#858585]">
                        <Activity className="size-3.5" />
                        ready
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>

          <aside className="space-y-4">
            {selectedProvider && (
              <div className="overflow-hidden rounded-xl border border-[#e8e8e8] bg-white shadow-[0_10px_30px_rgba(20,20,20,0.025)]">
                <div className="border-b border-[#eeeeea] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs text-[#858585]">{providerTypeLabel(selectedProvider.provider_type)}</p>
                      <h2 className="mt-1 truncate text-base font-medium text-[#1a1a1a]">
                        {selectedProvider.name}
                      </h2>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label="编辑供应商"
                        onClick={() => openEditDialog(selectedProvider)}
                      >
                        <Pencil className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label="删除供应商"
                        className="text-destructive"
                        onClick={() => void deleteProvider(selectedProvider)}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {selectedProvider.is_default ? (
                      <Badge variant="secondary" className="bg-[#e9f8ef] text-[#168a4a]">
                        default
                      </Badge>
                    ) : (
                      <Button
                        variant="outline"
                        size="xs"
                        className="rounded-full"
                        onClick={() => void markDefault(selectedProvider)}
                      >
                        设为默认
                      </Button>
                    )}
                    <Badge variant="secondary" className="bg-[#f4f4f4] text-[#5d5d5d]">
                      更新于 {formatDate(selectedProvider.updated_at)}
                    </Badge>
                  </div>
                </div>

                <div className="space-y-4 p-4">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="rounded-lg border border-[#eeeeea] bg-[#fbfbfa] p-3">
                      <p className="text-xs text-[#858585]">状态</p>
                      <div className="mt-2 flex items-center gap-1.5 text-sm font-medium text-[#168a4a]">
                        <ShieldCheck className="size-4" />
                        enabled
                      </div>
                    </div>
                    <div className="rounded-lg border border-[#eeeeea] bg-[#fbfbfa] p-3">
                      <p className="text-xs text-[#858585]">模型数</p>
                      <p className="mt-2 text-sm font-medium text-[#1a1a1a]">
                        {selectedProvider.models.length} routed
                      </p>
                    </div>
                  </div>

                  <div>
                    <p className="mb-2 text-xs text-[#858585]">模型</p>
                    {selectedProvider.models.length === 0 ? (
                      <div className="rounded-md border border-dashed border-[#d9d9d9] bg-[#fafafa] px-3 py-6 text-center text-sm text-[#858585]">
                        未配置模型
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {selectedProvider.models.map((model) => (
                          <div
                            key={`${model.model_name}-${model.litellm_model}`}
                            className="rounded-lg border border-[#e8e8e8] p-3"
                          >
                            <div className="min-w-0">
                              <p className="truncate text-sm font-medium text-[#1a1a1a]">
                                {model.display_name ?? model.model_name}
                              </p>
                              <p className="mt-1 truncate font-mono text-xs text-[#858585]">
                                {model.litellm_model}
                              </p>
                            </div>
                            <div className="mt-2">
                              <CapabilityBadges model={model} />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="rounded-xl border border-[#e8e8e8] bg-[#fafafa] p-3">
                    <div className="mb-3 flex items-center gap-2">
                      <KeyRound className="size-4 text-[#858585]" />
                      <p className="text-sm font-medium text-[#1a1a1a]">Gateway</p>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex min-w-0 items-center justify-between gap-2 rounded-md bg-white px-2.5 py-2">
                        <span className="truncate font-mono text-xs text-[#5d5d5d]">
                          {gateway?.gateway_base_url ?? "not ready"}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          aria-label="复制 Gateway URL"
                          onClick={() => void copyText(gateway?.gateway_base_url, "Gateway URL")}
                        >
                          <Copy className="size-3" />
                        </Button>
                      </div>
                      <div className="flex min-w-0 items-center justify-between gap-2 rounded-md bg-white px-2.5 py-2">
                        <span className="truncate font-mono text-xs text-[#5d5d5d]">
                          {maskSecret(gateway?.gateway_key)}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          aria-label="复制 Gateway Key"
                          onClick={() => void copyText(gateway?.gateway_key, "Gateway Key")}
                        >
                          <Copy className="size-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </aside>
        </div>
      )}

      <ProviderFormDialog
        open={isDialogOpen}
        provider={editingProvider}
        onOpenChange={setIsDialogOpen}
        onSaved={() => void refreshAll()}
      />
    </div>
  )
}
