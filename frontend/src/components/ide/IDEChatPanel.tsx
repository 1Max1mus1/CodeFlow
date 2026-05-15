import { useEffect, useRef, useState } from 'react'
import { chatWithAIStream } from '../../services/api'
import { MarkdownMessage } from './MarkdownMessage'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface IDEChatPanelProps {
  sessionId: string | null
  contextNodeId: string | null
  contextNodeName: string | null
}

export function IDEChatPanel({ sessionId, contextNodeId, contextNodeName }: IDEChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage() {
    const text = input.trim()
    if (!text || !sessionId || isLoading) return

    const userMsg: Message = { role: 'user', content: text }
    const next = [...messages, userMsg]
    const assistantIndex = next.length
    setMessages([...next, { role: 'assistant', content: '' }])
    setInput('')
    setIsLoading(true)

    try {
      await chatWithAIStream(sessionId, text, contextNodeId, messages, (token) => {
        setMessages((current) => {
          const updated = [...current]
          const assistant = updated[assistantIndex]
          if (!assistant || assistant.role !== 'assistant') return current
          updated[assistantIndex] = {
            ...assistant,
            content: assistant.content + token,
          }
          return updated
        })
      })
    } catch (err) {
      const raw = err instanceof Error ? err.message : 'Unknown error'
      const display = raw.includes('404')
        ? 'Session not found. The backend may have restarted. Please reload your project and start a new session.'
        : `Error: ${raw}`
      setMessages((current) => {
        const updated = [...current]
        const lastIndex = updated.length - 1
        if (updated[lastIndex]?.role === 'assistant') {
          updated[lastIndex] = { role: 'assistant', content: display }
          return updated
        }
        return [...next, { role: 'assistant', content: display }]
      })
    } finally {
      setIsLoading(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {contextNodeName && (
        <div className="px-3 py-1.5 border-b border-gray-700 bg-gray-850 text-xs text-blue-400 font-mono shrink-0">
          Context: {contextNodeName}()
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-xs text-gray-600 leading-relaxed">
            <p className="mb-2">Ask me anything about this project:</p>
            {[
              'What does the main() function do?',
              'How is authentication handled?',
              'Add a logging decorator to all route handlers',
              'Refactor the database connection logic',
            ].map((s) => (
              <button
                key={s}
                onClick={() => setInput(s)}
                className="block w-full text-left text-gray-500 hover:text-gray-300 hover:bg-gray-800 rounded px-2 py-1 transition-colors mb-1"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[90%] rounded-lg px-3 py-2 text-xs leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-blue-700 text-white rounded-br-none whitespace-pre-wrap'
                  : 'bg-gray-800 text-gray-200 rounded-bl-none'
              }`}
            >
              {msg.role === 'assistant' ? (
                msg.content ? (
                  <MarkdownMessage content={msg.content} />
                ) : (
                  <span className="animate-pulse text-gray-400">Thinking...</span>
                )
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      <div className="shrink-0 border-t border-gray-700 p-2">
        {!sessionId && (
          <p className="text-xs text-gray-600 text-center py-1">
            Load a project and open a session to chat
          </p>
        )}
        {sessionId && (
          <div className="flex gap-2 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about the code... (Enter to send, Shift+Enter for newline)"
              rows={2}
              className="flex-1 bg-gray-800 border border-gray-600 rounded text-xs text-gray-200 placeholder-gray-600 px-2 py-1.5 resize-none focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold px-3 py-2 rounded transition-colors shrink-0"
            >
              Send
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
