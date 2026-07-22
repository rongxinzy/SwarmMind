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

type AuthMode = "login" | "setup"

export function LoginPage() {
  const { hasUsers, login, setup } = useAuth()
  const [mode, setMode] = useState<AuthMode>(hasUsers === false ? "setup" : "login")
  const [identifier, setIdentifier] = useState("")
  const [email, setEmail] = useState("")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [displayName, setDisplayName] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isSetup = mode === "setup"

  async function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault()
    setIsLoading(true)
    setError(null)
    try {
      if (isSetup) {
        await setup(email, password, username || undefined, displayName || undefined)
      } else {
        await login(identifier, password)
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
            {isSetup ? "创建管理员账号" : "登录 SwarmMind"}
          </h1>
          <p className="mt-3 max-w-[300px] text-sm leading-6 text-[#5d5d5d]">
            Chat / Work 双模式的 Agent 聊天软件。
          </p>
        </div>

        <form onSubmit={handleSubmit} className="w-full">
          <FieldGroup className="gap-3">
            {isSetup && (
              <>
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
                  <FieldLabel htmlFor="username" className="sr-only">
                    用户名
                  </FieldLabel>
                  <Input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="用户名（可选，默认取邮箱前缀）"
                    autoComplete="username"
                    className="h-12 rounded-full border-[#d9d9d9] bg-white px-5 text-sm shadow-none"
                  />
                </Field>
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
              </>
            )}
            {!isSetup && (
              <Field>
                <FieldLabel htmlFor="identifier" className="sr-only">
                  邮箱或用户名
                </FieldLabel>
                <Input
                  id="identifier"
                  type="text"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="邮箱或用户名"
                  autoComplete="username"
                  required
                  className="h-12 rounded-full border-[#d9d9d9] bg-white px-5 text-sm shadow-none"
                />
              </Field>
            )}
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

        <div className="mt-6 flex flex-col items-center gap-2 text-center text-xs leading-5 text-[#858585]">
          {isSetup ? (
            <>
              <span>已有账号？</span>
              <button
                type="button"
                onClick={() => setMode("login")}
                className="text-[#141414] underline underline-offset-4 hover:text-[#5d5d5d]"
              >
                去登录
              </button>
            </>
          ) : (
            <>
              <span>还没有账号？</span>
              <button
                type="button"
                onClick={() => setMode("setup")}
                className="text-[#141414] underline underline-offset-4 hover:text-[#5d5d5d]"
              >
                创建管理员账号
              </button>
            </>
          )}
        </div>

        <p className="mt-6 text-center text-xs leading-5 text-[#858585]">
          本地账号用于保护会话历史、项目记录和算力配置。
        </p>
      </main>
    </div>
  )
}
