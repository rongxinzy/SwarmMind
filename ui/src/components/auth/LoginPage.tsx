import { useState } from "react"
import { useAuth } from "@/hooks/useAuth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
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

  async function handleSubmit(e: React.FormEvent) {
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
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>{isSetup ? "初始化账号" : "登录 SwarmMind"}</CardTitle>
          <CardDescription>
            {isSetup ? "创建第一个管理员账号" : "使用本地账号登录"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit}>
            <FieldGroup>
              {isSetup && (
                <Field>
                  <FieldLabel htmlFor="displayName">显示名称</FieldLabel>
                  <Input
                    id="displayName"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="可选"
                  />
                </Field>
              )}
              <Field>
                <FieldLabel htmlFor="email">邮箱</FieldLabel>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="password">密码</FieldLabel>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </Field>
              {error && <FieldError>{error}</FieldError>}
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Spinner data-icon="inline-start" />
                    处理中…
                  </>
                ) : isSetup ? (
                  "创建账号"
                ) : (
                  "登录"
                )}
              </Button>
            </FieldGroup>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
