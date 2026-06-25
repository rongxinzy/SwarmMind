import { AuthProvider, useAuth } from "@/hooks/useAuth"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Spinner } from "@/components/ui/spinner"
import { Toaster } from "sonner"
import { AppShell } from "@/components/layout/AppShell"
import { LoginPage } from "@/components/auth/LoginPage"

function AuthGate() {
  const { isLoading, isAuthenticated } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner className="size-6" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <LoginPage />
  }

  return <AppShell />
}

export default function App() {
  return (
    <AuthProvider>
      <TooltipProvider>
        <AuthGate />
        <Toaster position="top-right" />
      </TooltipProvider>
    </AuthProvider>
  )
}
