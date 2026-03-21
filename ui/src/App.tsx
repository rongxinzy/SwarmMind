import { useState } from "react"
import { Sidebar, SidebarView, VIEW_LABELS } from "@/components/ui/sidebar"
import { V0Chat } from "@/components/ui/v0-ai-chat"
import { FolderKanban, Search, Bot, Library } from "lucide-react"

// ---- Placeholder Views ----

function PlaceholderView({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
      <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center">
        {Icon}
      </div>
      <div>
        <h2 className="text-xl font-semibold text-foreground">{title}</h2>
        <p className="text-sm text-muted-foreground mt-1">{description}</p>
      </div>
    </div>
  )
}

// ---- Main App ----

export default function App() {
  const [activeView, setActiveView] = useState<SidebarView>("tasks")
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(undefined)
  const [conversationRefreshTrigger, setConversationRefreshTrigger] = useState(0)

  const handleConversationSelect = (conversationId: string) => {
    setActiveConversationId(conversationId)
  }

  const handleViewChange = (view: SidebarView) => {
    setActiveView(view)
    setActiveConversationId(undefined)
  }

  const renderContent = () => {
    switch (activeView) {
      case "tasks":
        return (
          <V0Chat
            conversationId={activeConversationId}
            onConversationCreated={(id) => {
              setActiveConversationId(id)
              setConversationRefreshTrigger((n) => n + 1)
            }}
          />
        )
      case "projects":

      case "projects":
        return (
          <PlaceholderView
            icon={<FolderKanban className="w-8 h-8 text-muted-foreground" />}
            title="Project Management"
            description="Manage your projects and track progress"
          />
        )

      case "search":
        return (
          <PlaceholderView
            icon={<Search className="w-8 h-8 text-muted-foreground" />}
            title="Search"
            description="Search across all agent contexts and memories"
          />
        )

      case "agents":
        return (
          <PlaceholderView
            icon={<Bot className="w-8 h-8 text-muted-foreground" />}
            title="Agents"
            description="Configure and monitor your AI agent team"
          />
        )

      case "library":
        return (
          <PlaceholderView
            icon={<Library className="w-8 h-8 text-muted-foreground" />}
            title="Library"
            description="Browse shared context and knowledge base"
          />
        )

      default:
        return null
    }
  }

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar
        activeView={activeView}
        onViewChange={handleViewChange}
        pageTitle={VIEW_LABELS[activeView]}
        onConversationSelect={handleConversationSelect}
        activeConversationId={activeConversationId}
        conversationRefreshTrigger={conversationRefreshTrigger}
      />

      <main className="flex-1 flex flex-col md:ml-64">
        {/* Desktop Header */}
        <header className="hidden md:flex border-b bg-background/95 backdrop-blur px-6 py-4 items-center">
          <h1 className="text-lg font-semibold">{VIEW_LABELS[activeView]}</h1>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-auto pt-14 md:pt-[65px]">
          {renderContent()}
        </div>
      </main>
    </div>
  )
}
