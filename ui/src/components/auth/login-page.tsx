import { type FormEvent, useState } from "react";
import { Sparkles } from "lucide-react";

import { useAuth } from "@/core/auth/context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function LoginPage() {
  const { hasUsers, login, setup } = useAuth();
  const isSetup = hasUsers === false;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      if (isSetup) {
        await setup(email, password, displayName || undefined);
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败，请重试");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-8">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex size-12 items-center justify-center rounded-2xl border border-border bg-secondary text-foreground">
            <Sparkles className="size-5" />
          </div>
          <div className="space-y-1">
            <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-foreground">
              SwarmMind
            </h1>
            <p className="text-[13px] text-muted-foreground">
              {isSetup ? "创建管理员账户以开始使用" : "登录到您的账户"}
            </p>
          </div>
        </div>

        <form onSubmit={(e) => { void handleSubmit(e); }} className="space-y-4">
          {isSetup && (
            <div className="space-y-1.5">
              <label htmlFor="displayName" className="text-[13px] font-medium text-foreground">
                显示名称
              </label>
              <Input
                id="displayName"
                type="text"
                placeholder="你的名字"
                value={displayName}
                onChange={(e) => { setDisplayName(e.target.value); }}
                autoComplete="name"
              />
            </div>
          )}

          <div className="space-y-1.5">
            <label htmlFor="email" className="text-[13px] font-medium text-foreground">
              邮箱
            </label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => { setEmail(e.target.value); }}
              required
              autoComplete="email"
              autoFocus
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="text-[13px] font-medium text-foreground">
              密码
            </label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => { setPassword(e.target.value); }}
              required
              autoComplete={isSetup ? "new-password" : "current-password"}
            />
          </div>

          {error && (
            <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-[13px] text-destructive">
              {error}
            </p>
          )}

          <Button
            type="submit"
            className="w-full"
            disabled={isSubmitting}
          >
            {isSubmitting
              ? isSetup ? "创建中..." : "登录中..."
              : isSetup ? "创建账户" : "登录"}
          </Button>
        </form>
      </div>
    </div>
  );
}
