import React, { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  Sparkles,
  Send,
  Loader2,
  Plus,
  Trash2,
  Bot,
  User as UserIcon,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  Cpu,
  ArrowRight,
  Terminal,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { FormattedMarkdown } from '@/components/FormattedMarkdown'
import { useAuth } from '@/context/AuthContext'
import { apiService } from '@/services/api'
import type {
  ConversationSummary,
  ConversationDetailResponse,
  ConversationMessageResponse,
} from '@/types'

export const AssistantPage: React.FC = () => {
  const { user } = useAuth()

  // State
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ConversationMessageResponse[]>([])
  const [inputText, setInputText] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [expandedTools, setExpandedTools] = useState<Record<string, boolean>>({})
  const [aiProvider, setAiProvider] = useState<string>('Google Gemini (gemini-2.5-flash)')
  const [isFallbackMode, setIsFallbackMode] = useState<boolean>(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  // Load user conversations on mount
  const loadConversation = async (conversationId: string) => {
    setLoadingHistory(true)
    setErrorMsg(null)
    try {
      const data: ConversationDetailResponse = await apiService.getConversation(conversationId)
      setActiveConversationId(data.id)
      setMessages(data.messages || [])
    } catch {
      setErrorMsg('Failed to load conversation history.')
    } finally {
      setLoadingHistory(false)
    }
  }

  const fetchConversations = async () => {
    try {
      const data = await apiService.listConversations()
      setConversations(data)
      if (data.length > 0 && !activeConversationId) {
        loadConversation(data[0].id)
      }
    } catch (err: unknown) {
      console.error('Failed to load conversations:', err)
    }
  }

  useEffect(() => {
    fetchConversations()
  }, [])

  const handleNewConversation = () => {
    setActiveConversationId(null)
    setMessages([])
    setErrorMsg(null)
  }

  const handleDeleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!window.confirm('Are you sure you want to delete this conversation thread?')) return

    try {
      await apiService.deleteConversation(convId)
      const remaining = conversations.filter((c) => c.id !== convId)
      setConversations(remaining)
      if (activeConversationId === convId) {
        if (remaining.length > 0) {
          loadConversation(remaining[0].id)
        } else {
          handleNewConversation()
        }
      }
    } catch (err: unknown) {
      console.error('Delete conversation error:', err)
      setErrorMsg('Failed to delete conversation.')
    }
  }

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim()
    if (!text || loading) return

    setInputText('')
    setErrorMsg(null)

    // Optimistic user message insertion
    const tempUserMsg: ConversationMessageResponse = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])
    setLoading(true)

    try {
      const response = await apiService.sendChatMessage({
        message: text,
        conversation_id: activeConversationId,
      })

      setActiveConversationId(response.conversation_id)
      setAiProvider(response.ai_provider)
      setIsFallbackMode(response.fallback_mode)

      const assistantMsg: ConversationMessageResponse = {
        id: response.message_id,
        role: 'assistant',
        content: response.response_text,
        tool_calls: response.tool_calls,
        tool_results: response.tool_results,
        proposal_id: response.proposal_preview?.proposal_id,
        created_at: response.created_at,
      }

      setMessages((prev) => [...prev, assistantMsg])

      // Refresh sidebar threads
      fetchConversations()
    } catch (err: any) {
      console.error('Chat error:', err)
      const errorDetail = err.response?.data?.detail || 'Failed to communicate with AI Assistant.'
      setErrorMsg(errorDetail)
    } finally {
      setLoading(false)
    }
  }

  const toggleToolsAccordion = (msgId: string) => {
    setExpandedTools((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }))
  }

  const quickPrompts = [
    { label: 'Active Surplus', prompt: 'What surplus food is available in the network right now?' },
    { label: 'Receiver Demands', prompt: 'What active demand requests are currently open?' },
    { label: 'Shelf-Life Urgency', prompt: 'How does the perishability intelligence engine determine decay rates and urgency?' },
    ...(user?.role === 'COORDINATOR' || user?.role === 'ADMIN'
      ? [{ label: 'Run Allocation Optimizer', prompt: 'Run allocation optimization to match available surplus with receiver demands.' }]
      : []),
  ]

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col md:flex-row bg-background overflow-hidden">
      {/* Left Sidebar: Conversations Thread List */}
      <aside className="w-full md:w-80 border-r border-border bg-card/60 flex flex-col flex-shrink-0">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            <span className="font-bold text-sm tracking-tight text-foreground">AI Copilot Threads</span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleNewConversation}
            className="gap-1.5 text-xs font-semibold h-8"
          >
            <Plus className="h-3.5 w-3.5" />
            New Chat
          </Button>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
          {conversations.length === 0 ? (
            <div className="text-center py-8 text-xs text-muted-foreground px-4">
              <Sparkles className="h-6 w-6 mx-auto mb-2 text-primary/40" />
              No previous threads. Ask the copilot anything to begin.
            </div>
          ) : (
            conversations.map((conv) => {
              const isActive = conv.id === activeConversationId
              return (
                <div
                  key={conv.id}
                  onClick={() => loadConversation(conv.id)}
                  className={`group flex items-center justify-between p-2.5 rounded-lg text-xs cursor-pointer transition-all ${
                    isActive
                      ? 'bg-primary/10 text-primary font-semibold border border-primary/20 shadow-sm'
                      : 'hover:bg-muted text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <div className="flex-1 truncate mr-2">
                    <p className="truncate text-foreground font-medium">{conv.title}</p>
                    <span className="text-[10px] text-muted-foreground">
                      {new Date(conv.updated_at).toLocaleDateString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                  <button
                    onClick={(e) => handleDeleteConversation(conv.id, e)}
                    className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive p-1 rounded transition-opacity"
                    title="Delete Thread"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              )
            })
          )}
        </div>

        {/* Sidebar Footer info */}
        <div className="p-3 border-t border-border bg-muted/20 text-[11px] text-muted-foreground flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
            Human-in-the-Loop
          </span>
          <span className="font-mono text-[10px]">{user?.role}</span>
        </div>
      </aside>

      {/* Main Chat Stream */}
      <main className="flex-1 flex flex-col h-full bg-background relative overflow-hidden">
        {/* Stream Top Header */}
        <header className="px-6 py-3 border-b border-border bg-card/40 flex items-center justify-between flex-shrink-0">
          <div>
            <h1 className="text-sm font-bold flex items-center gap-2 text-foreground">
              <Sparkles className="h-4 w-4 text-primary" />
              Redistribution Intelligence Copilot
            </h1>
            <p className="text-[11px] text-muted-foreground">
              Move food before time runs out &bull; Deterministic tools &amp; OR-Tools solver
            </p>
          </div>

          <div className="flex items-center gap-2">
            {isFallbackMode ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-600 border border-amber-500/20">
                <AlertTriangle className="h-3 w-3" />
                Deterministic Fallback Active
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-primary/10 text-primary border border-primary/20">
                <Cpu className="h-3 w-3" />
                {aiProvider}
              </span>
            )}
          </div>
        </header>

        {/* Error Alert Banner */}
        {errorMsg && (
          <div className="bg-destructive/10 border-b border-destructive/20 text-destructive text-xs px-6 py-2 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Messages Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {loadingHistory ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground space-y-2">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <p className="text-xs">Loading conversation history...</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full max-w-xl mx-auto text-center py-12 px-4 space-y-6">
              <div className="h-14 w-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center shadow-inner">
                <Bot className="h-8 w-8" />
              </div>
              <div className="space-y-2">
                <h2 className="text-lg font-bold tracking-tight text-foreground">
                  Food Has a Deadline &bull; AI Coordination Copilot
                </h2>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  I orchestrate deterministic tools to rescue perishable food. Ask about active surplus inventory,
                  receiver demands, shelf-life decay, road transit times, or run mathematical optimization.
                </p>
              </div>

              {/* Quick start prompts */}
              <div className="w-full space-y-2">
                <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Suggested Prompts
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                  {quickPrompts.map((qp, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(qp.prompt)}
                      className="p-3 rounded-lg border border-border bg-card/60 hover:bg-muted/60 hover:border-primary/30 transition-all text-xs group flex items-start justify-between"
                    >
                      <div>
                        <div className="font-semibold text-foreground group-hover:text-primary mb-1">
                          {qp.label}
                        </div>
                        <div className="text-[11px] text-muted-foreground line-clamp-2">
                          {qp.prompt}
                        </div>
                      </div>
                      <ArrowRight className="h-3.5 w-3.5 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-transform mt-0.5 ml-2 flex-shrink-0" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.role === 'user'
              const tools = msg.tool_calls || []
              const hasTools = tools.length > 0
              const isToolsExpanded = !!expandedTools[msg.id]

              return (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  {!isUser && (
                    <div className="h-8 w-8 rounded-lg bg-primary/10 border border-primary/20 text-primary flex items-center justify-center flex-shrink-0 mt-0.5">
                      <Bot className="h-4 w-4" />
                    </div>
                  )}

                  <div className={`max-w-[85%] sm:max-w-[75%] space-y-2`}>
                    {/* Message Bubble */}
                    <div
                      className={`p-4 rounded-2xl text-xs leading-relaxed shadow-sm ${
                        isUser
                          ? 'bg-primary text-primary-foreground rounded-br-none'
                          : 'bg-card border border-border text-foreground rounded-bl-none'
                      }`}
                    >
                      {/* Markdown rendered / formatted message content */}
                      <div className="break-words prose-xs">
                        <FormattedMarkdown content={msg.content} />
                      </div>

                      {/* Tool Calls Accordion */}
                      {hasTools && (
                        <div className="mt-3 pt-3 border-t border-border/40">
                          <button
                            onClick={() => toggleToolsAccordion(msg.id)}
                            className="flex items-center gap-1.5 text-[11px] font-semibold text-muted-foreground hover:text-foreground transition-colors"
                          >
                            <Terminal className="h-3.5 w-3.5 text-primary" />
                            <span>Executed Tools ({tools.length})</span>
                            {isToolsExpanded ? (
                              <ChevronDown className="h-3 w-3" />
                            ) : (
                              <ChevronRight className="h-3 w-3" />
                            )}
                          </button>

                          {isToolsExpanded && (
                            <div className="mt-2 space-y-2">
                              {tools.map((tc, tIdx) => {
                                const toolResult = (msg.tool_results || []).find(
                                  (tr) => tr.call_id === tc.call_id || tr.tool_name === tc.tool_name
                                )
                                const isSuccess = toolResult ? toolResult.success : true

                                return (
                                  <div
                                    key={tIdx}
                                    className="p-2.5 rounded-md bg-muted/50 border border-border/60 text-[11px] font-mono"
                                  >
                                    <div className="flex items-center justify-between mb-1">
                                      <span className="font-semibold text-primary">{tc.tool_name}</span>
                                      {isSuccess ? (
                                        <span className="flex items-center gap-1 text-[10px] text-emerald-600 font-bold">
                                          <CheckCircle2 className="h-3 w-3" />
                                          SUCCESS
                                        </span>
                                      ) : (
                                        <span className="flex items-center gap-1 text-[10px] text-destructive font-bold">
                                          <AlertTriangle className="h-3 w-3" />
                                          ERROR
                                        </span>
                                      )}
                                    </div>
                                    <div className="text-[10px] text-muted-foreground">
                                      Args: {JSON.stringify(tc.arguments)}
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Proposal Preview Card if present */}
                    {msg.proposal_id && (
                      <div className="p-4 rounded-xl border-2 border-amber-500/40 bg-amber-500/5 shadow-sm space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-bold bg-amber-500/20 text-amber-800 dark:text-amber-300">
                            <AlertTriangle className="h-3.5 w-3.5" />
                            DRAFT PROPOSAL — AWAITING HUMAN APPROVAL
                          </span>
                          <span className="text-[10px] text-muted-foreground font-mono">
                            ID: {msg.proposal_id.slice(0, 8)}...
                          </span>
                        </div>

                        <p className="text-xs text-muted-foreground">
                          A mathematically constrained allocation proposal has been drafted using Google OR-Tools.
                          Surplus inventory has <strong>NOT</strong> been committed.
                        </p>

                        <div className="flex items-center justify-end pt-1">
                          <Link to="/coordinator/optimization">
                            <Button size="sm" variant="default" className="gap-1.5 text-xs font-semibold">
                              <Cpu className="h-3.5 w-3.5" />
                              Review in Optimizer Workspace
                              <ArrowRight className="h-3.5 w-3.5" />
                            </Button>
                          </Link>
                        </div>
                      </div>
                    )}

                    <div
                      className={`text-[10px] text-muted-foreground px-1 ${
                        isUser ? 'text-right' : 'text-left'
                      }`}
                    >
                      {new Date(msg.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  </div>

                  {isUser && (
                    <div className="h-8 w-8 rounded-lg bg-primary text-primary-foreground flex items-center justify-center flex-shrink-0 mt-0.5">
                      <UserIcon className="h-4 w-4" />
                    </div>
                  )}
                </div>
              )
            })
          )}

          {/* Typing Indicator */}
          {loading && (
            <div className="flex gap-3 justify-start">
              <div className="h-8 w-8 rounded-lg bg-primary/10 border border-primary/20 text-primary flex items-center justify-center flex-shrink-0">
                <Bot className="h-4 w-4" />
              </div>
              <div className="p-3.5 rounded-2xl rounded-bl-none bg-card border border-border text-xs flex items-center gap-2 text-muted-foreground shadow-sm">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                <span>AI Copilot is reasoning and coordinating tools...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <footer className="p-4 border-t border-border bg-card/40 flex-shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSendMessage()
            }}
            className="flex items-end gap-2 max-w-4xl mx-auto"
          >
            <div className="flex-1 relative">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSendMessage()
                  }
                }}
                placeholder="Ask the redistribution copilot (e.g. 'What surplus food is expiring today?')..."
                rows={2}
                maxLength={4000}
                disabled={loading}
                className="w-full resize-none rounded-xl border border-input bg-background px-3.5 py-2.5 text-xs text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary shadow-sm disabled:opacity-50"
              />
              <span className="absolute right-3 bottom-2 text-[10px] text-muted-foreground pointer-events-none">
                {inputText.length}/4000
              </span>
            </div>

            <Button
              type="submit"
              disabled={loading || !inputText.trim()}
              className="h-11 px-4 rounded-xl gap-1.5 text-xs font-semibold"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  <span className="hidden sm:inline">Send</span>
                </>
              )}
            </Button>
          </form>

          <p className="text-[10px] text-center text-muted-foreground mt-2">
            Safety Boundary: AI Copilot prepares and explains proposals. Human coordinator approval is required before food is committed.
          </p>
        </footer>
      </main>
    </div>
  )
}

export default AssistantPage
