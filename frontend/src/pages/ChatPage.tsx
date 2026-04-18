import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Settings2, Trash2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import DomainSelector from '../components/DomainSelector'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const DOMAINS = [
  { value: 'general', label: '通用', description: '一般 Abaqus 问题' },
  { value: 'geotechnical', label: '岩土', description: '岩土工程分析' },
  { value: 'structural', label: '结构', description: '结构工程分析' },
  { value: 'mechanical', label: '机械', description: '机械工程分析' },
  { value: 'thermal', label: '热分析', description: '传热与热应力' },
  { value: 'impact', label: '冲击', description: '动态冲击分析' },
  { value: 'composite', label: '复合材料', description: '复合材料建模' },
  { value: 'biomechanics', label: '生物力学', description: '生物医学分析' },
  { value: 'electromagnetic', label: '电磁', description: '电磁场分析' },
]

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [domain, setDomain] = useState('general')
  const [showSettings, setShowSettings] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.content,
          domain,
          history: messages.slice(-10).map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      })

      if (!response.ok) throw new Error('请求失败')

      // Handle streaming response
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ''

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') continue
              try {
                const parsed = JSON.parse(data)
                if (parsed.content) {
                  assistantContent += parsed.content
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMessage.id
                        ? { ...m, content: assistantContent }
                        : m
                    )
                  )
                }
              } catch {
                // Ignore parsing errors
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error)
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: '抱歉，发生了错误。请稍后重试。',
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const clearChat = () => {
    setMessages([])
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-dark-800">
        <div>
          <h2 className="text-lg font-semibold">智能对话</h2>
          <p className="text-sm text-dark-400">与 AI 讨论 Abaqus 相关问题</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 rounded-lg hover:bg-dark-800 transition-colors"
          >
            <Settings2 className="w-5 h-5 text-dark-400" />
          </button>
          <button
            onClick={clearChat}
            className="p-2 rounded-lg hover:bg-dark-800 transition-colors text-dark-400 hover:text-red-400"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Settings panel */}
      {showSettings && (
        <div className="px-6 py-4 border-b border-dark-800 bg-dark-900/50">
          <DomainSelector
            domains={DOMAINS}
            value={domain}
            onChange={setDomain}
          />
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-primary-500/20 to-primary-700/20 rounded-2xl flex items-center justify-center mb-4">
              <span className="text-3xl">🔧</span>
            </div>
            <h3 className="text-xl font-semibold mb-2">开始对话</h3>
            <p className="text-dark-400 max-w-md">
              向 AbaqusGPT 提问任何关于 Abaqus 有限元分析的问题，包括建模、
              网格划分、材料设置、边界条件、收敛问题等。
            </p>
            <div className="mt-6 flex flex-wrap gap-2 justify-center">
              {[
                '如何设置初始地应力？',
                'CDP 混凝土模型参数怎么设置？',
                '接触分析不收敛怎么办？',
                '如何优化网格质量？',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setInput(suggestion)}
                  className="px-3 py-1.5 bg-dark-800 hover:bg-dark-700 rounded-full text-sm text-dark-300 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-4 message-enter ${
                message.role === 'user' ? 'justify-end' : ''
              }`}
            >
              {message.role === 'assistant' && (
                <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-sm font-bold">A</span>
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-primary-600 text-white'
                    : 'bg-dark-800 text-dark-100'
                }`}
              >
                {message.role === 'assistant' ? (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown
                      components={{
                        code({ inline, className, children, ...props }) {
                          const match = /language-(\w+)/.exec(className || '')
                          return !inline && match ? (
                            <SyntaxHighlighter
                              style={oneDark}
                              language={match[1]}
                              PreTag="div"
                              {...props}
                            >
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          ) : (
                            <code className={className} {...props}>
                              {children}
                            </code>
                          )
                        },
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap">{message.content}</p>
                )}
              </div>
              {message.role === 'user' && (
                <div className="w-8 h-8 bg-dark-700 rounded-lg flex items-center justify-center flex-shrink-0">
                  <span className="text-dark-300 text-sm">👤</span>
                </div>
              )}
            </div>
          ))
        )}
        {isLoading && messages[messages.length - 1]?.role === 'user' && (
          <div className="flex gap-4">
            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-white text-sm font-bold">A</span>
            </div>
            <div className="bg-dark-800 rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <div className="loading-dot"></div>
                <div className="loading-dot"></div>
                <div className="loading-dot"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="px-6 py-4 border-t border-dark-800">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入您的问题..."
            className="input flex-1"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="btn btn-primary px-6"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
