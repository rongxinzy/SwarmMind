import { useState } from "react"
import { useAuth } from "@/hooks/useAuth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Spinner } from "@/components/ui/spinner"

export function LoginPage() {
  const { hasUsers, login, setup } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [displayName, setDisplayName] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isSetup = hasUsers === false

  async function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault()
    setIsLoading(true)
    setError(null)
    try {
      if (isSetup) {
        await setup(email, password, displayName || undefined)
      } else {
        await login(email, password)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f5f5f5] px-4 py-10 text-[#1a1a1a]">
      <main className="flex w-full max-w-[340px] flex-col items-center">
        <div className="mb-7 flex flex-col items-center text-center">
          <div className="mb-5 grid size-12 grid-cols-2 gap-1 rounded-2xl bg-[#141414] p-2 shadow-sm">
            <span className="rounded-[5px] bg-white" />
            <span className="rounded-[5px] bg-white/65" />
            <span className="rounded-[5px] bg-white/65" />
            <span className="rounded-[5px] bg-white" />
          </div>
          <h1 className="text-[28px] font-light leading-9">
            {isSetup ? "初始化 SwarmMind" : "登录 SwarmMind"}
          </h1>
          <p className="mt-3 max-w-[300px] text-sm leading-6 text-[#5d5d5d]">
            将团队灵感转化为可预览、可追踪、可继续推进的交付成果。
          </p>
        </div>

        <form onSubmit={handleSubmit} className="w-full">
          <FieldGroup className="gap-3">
            {isSetup && (
              <Field>
                <FieldLabel htmlFor="displayName" className="sr-only">
                  显示名称
                </FieldLabel>
                <Input
                  id="displayName"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="显示名称（可选）"
                  autoComplete="name"
                  className="h-12 rounded-full border-[#d9d9d9] bg-white px-5 text-sm shadow-none"
                />
              </Field>
            )}
            <Field>
              <FieldLabel htmlFor="email" className="sr-only">
                邮箱
              </FieldLabel>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="邮箱"
                autoComplete="email"
                required
                className="h-12 rounded-full border-[#d9d9d9] bg-white px-5 text-sm shadow-none"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="password" className="sr-only">
                密码
              </FieldLabel>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="密码"
                autoComplete={isSetup ? "new-password" : "current-password"}
                required
                className="h-12 rounded-full border-[#d9d9d9] bg-white px-5 text-sm shadow-none"
              />
            </Field>
            {error && <FieldError className="justify-center text-center">{error}</FieldError>}
            <Button
              type="submit"
              className="mt-1 h-12 w-full rounded-full bg-[#141414] text-sm font-medium text-white hover:bg-[#262626]"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Spinner data-icon="inline-start" />
                  处理中…
                </>
              ) : isSetup ? (
                "创建账号"
              ) : (
                "继续"
              )}
            </Button>
          </FieldGroup>
        </form>

        <p className="mt-6 text-center text-xs leading-5 text-[#858585]">
          本地账号用于保护项目记忆、来源证据和团队交付记录。
        </p>
      </main>
    </div>
  )
}
