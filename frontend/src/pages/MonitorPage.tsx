/**
 * Abaqus 工作目录实时监控页面 v2.0
 *
 * 布局：左侧文件浏览 | 中间 VSCode 风格代码查看 | 右侧 AI 智能体对话
 * 功能：
 * 1. 可拖拽调整中/右面板宽度
 * 2. 行号显示 + INP/MSG 基础语法高亮
 * 3. 多标签页同时打开多个文件
 * 4. Agent 步骤透明展示（读取了哪些文件、调用了什么模型）
 * 5. 多模型选择（GPT-4o / Claude / DeepSeek）
 * 6. 最近打开路径记忆
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import {
  FolderOpen, RefreshCw, FileText, AlertTriangle, CheckCircle,
  XCircle, Clock, Terminal, Send, ChevronRight, ChevronDown,
  Loader2, HardDrive, Zap, AlertCircle, Bot, GripVertical, Eye, Cpu, History, X,
  Folder, Pencil, Trash2, Copy, ClipboardPaste, FilePlus, FolderPlus,
} from 'lucide-react'

// ============================================================
// Types
// ============================================================

interface AgentStep {
  type: string
  step?: string
  message?: string
  file?: string
  size?: string
  model?: string
  tool?: string
  command?: string
  output?: string
  full_output?: string
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isCommand?: boolean
  commandResult?: { stdout?: string; stderr?: string; return_code?: number }
  agentSteps?: AgentStep[]
}

interface FileInfo {
  name: string
  path: string
  extension: string
  size: number
  modified: string
  category: string
  type_name: string
  is_running: boolean
}

interface JobStatus {
  job_name: string
  status: 'pending' | 'running' | 'completed' | 'error' | 'aborted' | 'unknown'
  progress?: number
  current_step?: number
  current_increment?: number
  errors: string[]
  warnings: string[]
  last_message?: string
}

interface WorkspaceStatus {
  path: string
  exists: boolean
  files: FileInfo[]
  jobs: JobStatus[]
  total_files: number
  abaqus_files: number
  last_update: string
}

interface OpenTab {
  file: FileInfo
  content: string
  isLoading: boolean
  isTruncated: boolean
}

interface TreeNode {
  name: string
  path: string
  type: 'file' | 'directory'
  size?: number
  extension?: string
  is_running?: boolean
  children?: TreeNode[]
}

interface ContextMenuState {
  x: number
  y: number
  node: TreeNode
}

// ============================================================
// Helpers
// ============================================================

const getStatusColor = (status: string) => {
  switch (status) {
    case 'running': return 'text-blue-400'
    case 'completed': case 'converged': return 'text-emerald-400'
    case 'error': case 'not_converged': return 'text-red-400'
    case 'warning': return 'text-yellow-400'
    default: return 'text-dark-500'
  }
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'running': return <Loader2 className="w-3.5 h-3.5 animate-spin" />
    case 'completed': case 'converged': return <CheckCircle className="w-3.5 h-3.5" />
    case 'error': case 'not_converged': return <XCircle className="w-3.5 h-3.5" />
    case 'warning': return <AlertTriangle className="w-3.5 h-3.5" />
    case 'pending': return <Clock className="w-3.5 h-3.5" />
    default: return <AlertCircle className="w-3.5 h-3.5" />
  }
}

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const getFileColor = (ext: string, isRunning: boolean) => {
  if (isRunning) return 'text-blue-400'
  switch (ext) {
    case 'inp': return 'text-cyan-400'
    case 'msg': return 'text-yellow-400'
    case 'sta': return 'text-emerald-400'
    case 'dat': return 'text-purple-400'
    case 'log': return 'text-slate-400'
    case 'odb': return 'text-orange-400'
    default: return 'text-dark-500'
  }
}

// ============================================================
// Sub-component: VSCode-style Code Viewer
// ============================================================

function getLineHighlight(line: string, ext: string): string {
  const trimmed = line.trim()
  if (ext === 'inp') {
    if (trimmed.startsWith('**')) return 'text-emerald-700'
    if (trimmed.startsWith('*') && !trimmed.startsWith('**')) return 'text-cyan-300 font-semibold'
  }
  if (ext === 'msg' || ext === 'log') {
    const lower = line.toLowerCase()
    if (lower.includes('***error')) return 'text-red-400 font-semibold'
    if (lower.includes('***warning') || lower.includes('***note')) return 'text-yellow-300'
    if (lower.includes('error')) return 'text-red-400'
    if (lower.includes('warning')) return 'text-yellow-400'
    if (lower.includes('attempt') || lower.includes('increment')) return 'text-sky-400/80'
  }
  if (ext === 'sta') {
    const lower = line.toLowerCase()
    if (lower.includes('cutback') || lower.includes('diverge')) return 'text-red-400'
    if (lower.includes('converge')) return 'text-emerald-400'
  }
  return 'text-slate-300'
}

function CodeViewer({ content, filename, isLoading, isTruncated }: {
  content: string; filename: string; isLoading: boolean; isTruncated?: boolean
}) {
  const [jumpLine, setJumpLine] = useState('')
  const [highlightedLine, setHighlightedLine] = useState<number | null>(null)
  const rowRefs = useRef<Map<number, HTMLTableRowElement>>(new Map())
  const ext = (filename.split('.').pop() || '').toLowerCase()
  const lines = useMemo(() => content.split('\n'), [content])

  const handleJump = () => {
    const n = parseInt(jumpLine)
    if (n > 0 && n <= lines.length) {
      const el = rowRefs.current.get(n)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        setHighlightedLine(n)
        setTimeout(() => setHighlightedLine(null), 2000)
      }
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-[#1e1e1e]">
        <div className="text-center">
          <Loader2 className="w-6 h-6 animate-spin text-primary-400 mx-auto mb-2" />
          <p className="text-xs text-dark-500">加载文件...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-[#1e1e1e]">
      {/* Toolbar */}
      <div className="flex-shrink-0 flex items-center gap-3 px-4 py-1.5 bg-[#252526] border-b border-[#3c3c3c] text-xs">
        <span className="text-[#858585]">{lines.length.toLocaleString()} 行</span>
        <span className="text-[#555]">|</span>
        <span className="text-primary-400 uppercase font-mono font-medium">{ext}</span>
        {isTruncated && (
          <>
            <span className="text-[#555]">|</span>
            <span className="text-amber-500 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" /> 文件过大，仅显示末尾内容
            </span>
          </>
        )}
        <div className="ml-auto flex items-center gap-1">
          <input
            type="number"
            min={1}
            max={lines.length}
            value={jumpLine}
            onChange={e => setJumpLine(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleJump()}
            placeholder="跳转行号..."
            className="w-24 bg-[#3c3c3c] border border-[#555] rounded px-2 py-0.5 text-xs text-[#ccc] focus:outline-none focus:border-primary-500 placeholder:text-[#555]"
          />
          <button onClick={handleJump} className="px-2 py-0.5 bg-[#3c3c3c] hover:bg-[#505050] rounded text-xs text-[#ccc]">
            Go
          </button>
        </div>
      </div>
      {/* Code */}
      <div className="flex-1 overflow-auto font-mono text-xs leading-5">
        <table className="min-w-full border-collapse">
          <tbody>
            {lines.map((line, i) => {
              const lineNum = i + 1
              const isHighlighted = highlightedLine === lineNum
              return (
                <tr
                  key={i}
                  ref={el => { if (el) rowRefs.current.set(lineNum, el); else rowRefs.current.delete(lineNum) }}
                  className={`group transition-colors ${isHighlighted ? 'bg-yellow-500/20' : 'hover:bg-white/5'}`}
                >
                  <td className="select-none text-right pr-4 pl-4 py-0 text-[#555] border-r border-[#3c3c3c] w-14 min-w-[3.5rem] leading-5 align-top group-hover:text-[#858585]">
                    {lineNum}
                  </td>
                  <td className="pl-5 pr-8 py-0 leading-5 whitespace-pre align-top">
                    <span className={getLineHighlight(line, ext)}>{line || '\u00A0'}</span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ============================================================
// Sub-component: Agent Steps
// ============================================================

const STEP_ICONS: Record<string, string> = {
  agent_init: '🧠', calling_llm: '🤖', thinking: '💭',
  tool_call: '⚡', tool_result: '✅',
  detecting_intent: '🔍', reading_file: '📄',
  building_context: '🔧',
}

function getStepLabel(step: AgentStep): string {
  const key = step.step || step.type
  if (key === 'agent_init') return step.message || '自主 Agent 模式'
  if (key === 'calling_llm') return step.message || `调用模型: ${step.model || 'LLM'}`
  if (key === 'thinking') return '思考中...'
  if (key === 'tool_call') return `${step.tool}`
  if (key === 'tool_result') return `${step.tool} 完成`
  if (key === 'detecting_intent') return step.message || '分析意图'
  if (key === 'reading_file') return `读取: ${step.file}${step.size ? ` (${step.size})` : ''}`
  if (key === 'building_context') return step.message || '构建上下文'
  return step.message || key
}

function AgentSteps({ steps }: { steps: AgentStep[] }) {
  const [expandedIdx, setExpandedIdx] = useState<Set<number>>(new Set())
  if (!steps.length) return null

  const toggle = (i: number) => {
    setExpandedIdx(prev => {
      const n = new Set(prev)
      n.has(i) ? n.delete(i) : n.add(i)
      return n
    })
  }

  // Group consecutive tool_call + tool_result into command blocks
  type StepGroup =
    | { kind: 'command'; call: AgentStep; result: AgentStep; idx: number }
    | { kind: 'single'; step: AgentStep; idx: number }
  const groups: StepGroup[] = []
  for (let i = 0; i < steps.length; i++) {
    const k = steps[i].step || steps[i].type
    if (k === 'tool_call' && i + 1 < steps.length && (steps[i + 1].step || steps[i + 1].type) === 'tool_result') {
      groups.push({ kind: 'command', call: steps[i], result: steps[i + 1], idx: i })
      i++
    } else {
      groups.push({ kind: 'single', step: steps[i], idx: i })
    }
  }

  return (
    <div className="mb-2 space-y-1.5">
      {groups.map((g, gi) => {
        // === Merged tool_call + tool_result: terminal-style command block ===
        if (g.kind === 'command') {
          const isExpanded = expandedIdx.has(g.idx)
          const fullOut = (g.result as any).full_output
          return (
            <div key={gi} className="rounded-lg border border-[#30363d] bg-[#0d1117] overflow-hidden text-xs">
              <div className="flex items-center gap-2 px-3 py-1 bg-[#161b22] border-b border-[#21262d]">
                <Terminal className="w-3 h-3 text-emerald-500" />
                <span className="font-medium text-emerald-400">{g.call.tool}</span>
              </div>
              {g.call.command && (
                <div className="px-3 py-1.5 font-mono text-[#e6edf3] border-b border-[#21262d]">
                  <span className="text-emerald-500 select-none">❯ </span>{g.call.command}
                </div>
              )}
              <div
                className={`px-3 py-1.5 flex items-center gap-2 ${fullOut ? 'cursor-pointer hover:bg-[#161b22]' : ''}`}
                onClick={() => fullOut && toggle(g.idx)}
              >
                <CheckCircle className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                <span className="flex-1 text-[#8b949e] truncate">{g.result.output?.slice(0, 100) || '完成'}</span>
                {fullOut && <span className="text-[#484f58] text-[10px] flex-shrink-0">{isExpanded ? '▲ 收起' : '▼ 展开输出'}</span>}
              </div>
              {fullOut && isExpanded && (
                <div className="border-t border-[#21262d] px-3 py-2 font-mono text-[10px] text-[#8b949e] leading-[1.6] max-h-60 overflow-auto whitespace-pre-wrap bg-[#010409]">
                  {fullOut}
                </div>
              )}
            </div>
          )
        }

        // === Single step ===
        const { step, idx } = g
        const key = step.step || step.type

        // Thinking block
        if (key === 'thinking') {
          const isExpanded = expandedIdx.has(idx)
          return (
            <div key={gi} className="rounded-lg border border-[#30363d] bg-[#161b22] overflow-hidden text-xs">
              <div className="flex items-center gap-2 px-3 py-1.5 text-[#8b949e] cursor-pointer hover:text-[#c9d1d9]"
                onClick={() => toggle(idx)}>
                <span>💭</span>
                <span className="flex-1 italic">思考过程</span>
                <span className="text-[10px] text-[#484f58]">{isExpanded ? '▲' : '▼'}</span>
              </div>
              {isExpanded && (
                <div className="px-3 pb-2 text-xs text-[#8b949e] italic leading-relaxed whitespace-pre-wrap border-t border-[#30363d] pt-2">
                  {step.message}
                </div>
              )}
            </div>
          )
        }

        // Standalone tool_call (result not yet received — show spinner)
        if (key === 'tool_call') {
          return (
            <div key={gi} className="rounded-lg border border-[#30363d] bg-[#0d1117] overflow-hidden text-xs">
              <div className="flex items-center gap-2 px-3 py-1 bg-[#161b22] border-b border-[#21262d]">
                <Terminal className="w-3 h-3 text-emerald-500" />
                <span className="font-medium text-emerald-400">{step.tool}</span>
              </div>
              {step.command && (
                <div className="px-3 py-1.5 font-mono text-[#e6edf3]">
                  <span className="text-emerald-500 select-none">❯ </span>{step.command}
                </div>
              )}
              <div className="px-3 py-1.5 flex items-center gap-2 text-[#484f58] border-t border-[#21262d]">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>执行中...</span>
              </div>
            </div>
          )
        }

        // Standalone tool_result
        if (key === 'tool_result') {
          const isExpanded = expandedIdx.has(idx)
          const fullOut = (step as any).full_output
          return (
            <div key={gi} className="rounded-lg border border-[#30363d] bg-[#0d1117] overflow-hidden text-xs">
              <div className={`px-3 py-1.5 flex items-center gap-2 ${fullOut ? 'cursor-pointer hover:bg-[#161b22]' : ''}`}
                onClick={() => fullOut && toggle(idx)}>
                <CheckCircle className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                <span className="flex-1 text-[#8b949e] truncate">{step.output?.slice(0, 100) || '完成'}</span>
                {fullOut && <span className="text-[#484f58] text-[10px]">{isExpanded ? '▲' : '▼'}</span>}
              </div>
              {fullOut && isExpanded && (
                <div className="border-t border-[#21262d] px-3 py-2 font-mono text-[10px] text-[#8b949e] leading-[1.6] max-h-60 overflow-auto whitespace-pre-wrap bg-[#010409]">
                  {fullOut}
                </div>
              )}
            </div>
          )
        }

        // Calling LLM iteration marker
        if (key === 'calling_llm') {
          return (
            <div key={gi} className="flex items-center gap-2 text-xs text-[#484f58] py-0.5">
              <span>🤖</span>
              <span>{step.message || `调用 ${step.model || 'LLM'}`}</span>
              <div className="flex-1 h-px bg-[#21262d]" />
            </div>
          )
        }

        // Default (agent_init, etc)
        return (
          <div key={gi} className="flex items-center gap-2 text-xs text-[#8b949e] py-0.5">
            <span>{STEP_ICONS[key] || '⚙️'}</span>
            <span>{getStepLabel(step)}</span>
          </div>
        )
      })}
    </div>
  )
}

// ============================================================
// Sub-component: FileTreeNode — VSCode style directory tree
// ============================================================

function FileTreeNodeView({
  node,
  depth,
  expandedDirs,
  toggleDir,
  onFileClick,
  activeFilePath,
  onContextMenu,
  renamingPath,
  renameValue,
  onRenameChange,
  onRenameSubmit,
  onRenameCancel,
}: {
  node: TreeNode
  depth: number
  expandedDirs: Set<string>
  toggleDir: (path: string) => void
  onFileClick: (node: TreeNode) => void
  activeFilePath: string | null
  onContextMenu: (e: React.MouseEvent, node: TreeNode) => void
  renamingPath: string | null
  renameValue: string
  onRenameChange: (v: string) => void
  onRenameSubmit: () => void
  onRenameCancel: () => void
}) {
  const isDir = node.type === 'directory'
  const isExpanded = expandedDirs.has(node.path)
  const paddingLeft = 8 + depth * 16
  const isRenaming = renamingPath === node.path

  if (isRenaming) {
    return (
      <div className="flex items-center gap-1 py-[2px]" style={{ paddingLeft: isDir ? paddingLeft : paddingLeft + 16 }}>
        {isDir && (isExpanded
          ? <FolderOpen className="w-3.5 h-3.5 flex-shrink-0 text-yellow-500" />
          : <Folder className="w-3.5 h-3.5 flex-shrink-0 text-yellow-600" />)}
        {!isDir && <FileText className={`w-3.5 h-3.5 flex-shrink-0 ${getFileColor((node.extension || '').replace('.', ''), !!node.is_running)}`} />}
        <input
          autoFocus
          className="flex-1 bg-dark-700 border border-primary-500 rounded px-1.5 py-0.5 text-xs font-mono text-white outline-none min-w-0"
          value={renameValue}
          onChange={e => onRenameChange(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') onRenameSubmit(); if (e.key === 'Escape') onRenameCancel() }}
          onBlur={onRenameSubmit}
          onClick={e => e.stopPropagation()}
        />
      </div>
    )
  }

  if (isDir) {
    return (
      <>
        <div
          className="flex items-center gap-1 py-[3px] cursor-pointer hover:bg-dark-800 text-dark-400 hover:text-dark-300 transition-colors select-none"
          style={{ paddingLeft }}
          onClick={() => toggleDir(node.path)}
          onContextMenu={(e) => onContextMenu(e, node)}
        >
          {isExpanded
            ? <ChevronDown className="w-3.5 h-3.5 flex-shrink-0 text-dark-500" />
            : <ChevronRight className="w-3.5 h-3.5 flex-shrink-0 text-dark-500" />}
          {isExpanded
            ? <FolderOpen className="w-3.5 h-3.5 flex-shrink-0 text-yellow-500" />
            : <Folder className="w-3.5 h-3.5 flex-shrink-0 text-yellow-600" />}
          <span className="text-xs truncate font-mono">{node.name}</span>
        </div>
        {isExpanded && node.children?.map(child => (
          <FileTreeNodeView
            key={child.path}
            node={child}
            depth={depth + 1}
            expandedDirs={expandedDirs}
            toggleDir={toggleDir}
            onFileClick={onFileClick}
            activeFilePath={activeFilePath}
            onContextMenu={onContextMenu}
            renamingPath={renamingPath}
            renameValue={renameValue}
            onRenameChange={onRenameChange}
            onRenameSubmit={onRenameSubmit}
            onRenameCancel={onRenameCancel}
          />
        ))}
      </>
    )
  }

  const ext = node.extension || ''
  const isActive = activeFilePath === node.path
  return (
    <div
      className={`flex items-center gap-1.5 py-[3px] cursor-pointer text-xs transition-colors select-none ${isActive ? 'bg-dark-700 text-white' : 'hover:bg-dark-800 text-dark-400'}`}
      style={{ paddingLeft: paddingLeft + 16 }}
      onClick={() => onFileClick(node)}
      onContextMenu={(e) => onContextMenu(e, node)}
    >
      <FileText className={`w-3.5 h-3.5 flex-shrink-0 ${getFileColor(ext.replace('.', ''), !!node.is_running)}`} />
      <span className="flex-1 truncate font-mono">{node.name}</span>
      {node.size != null && (
        <span className="text-dark-600 flex-shrink-0 pr-2 text-[10px]">{formatFileSize(node.size)}</span>
      )}
    </div>
  )
}

// ============================================================
// Sub-component: Resize Handle
// ============================================================

function ResizeHandle({ onMouseDown }: { onMouseDown: (e: React.MouseEvent) => void }) {
  return (
    <div
      className="w-1.5 flex-shrink-0 cursor-col-resize select-none flex items-center justify-center bg-[#3c3c3c] hover:bg-primary-600/50 transition-colors"
      onMouseDown={onMouseDown}
    >
      <GripVertical className="w-3 h-3 text-[#555] pointer-events-none" />
    </div>
  )
}

// ============================================================
// Models & Quick actions
// ============================================================

const AVAILABLE_MODELS = [
  { id: 'gpt-4o', label: 'GPT-4o', badge: 'OpenAI', color: 'text-emerald-400' },
  { id: 'gpt-4o-mini', label: 'GPT-4o Mini', badge: 'OpenAI', color: 'text-emerald-400' },
  { id: 'claude-opus-4-5', label: 'Claude Opus 4.5', badge: 'Anthropic', color: 'text-orange-400' },
  { id: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5', badge: 'Anthropic', color: 'text-orange-400' },
  { id: 'claude-3-7-sonnet-20250219', label: 'Claude 3.7 Sonnet', badge: 'Anthropic', color: 'text-orange-400' },
  { id: 'deepseek-chat', label: 'DeepSeek Chat', badge: 'DeepSeek', color: 'text-blue-400' },
  { id: 'deepseek/deepseek-r1', label: 'DeepSeek R1', badge: 'DeepSeek', color: 'text-blue-400' },
]

const QUICK_QUESTIONS = [
  { label: '分析收敛', q: '请分析当前作业的收敛问题，给出具体的解决建议和参数修改方案' },
  { label: '检查网格', q: '请检查当前模型的网格质量，是否存在严重扭曲或尺寸问题？' },
  { label: '解释错误', q: '请解释当前作业中的所有错误和警告信息，应该如何修复？' },
  { label: '优化参数', q: '当前计算参数是否合理？如何优化步长控制、收敛准则以提高效率？' },
  { label: '提交作业', q: '请帮我生成提交当前作业的命令（基于 inp 文件名）' },
]

// ============================================================
// Main Component
// ============================================================

export default function MonitorPage() {
  const [workspacePath, setWorkspacePath] = useState('')
  const [workspaceStatus, setWorkspaceStatus] = useState<WorkspaceStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set())
  const refreshIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [openTabs, setOpenTabs] = useState<Map<string, OpenTab>>(new Map())
  const [activeTabName, setActiveTabName] = useState<string | null>(null)

  // Directory tree state
  const [fileTree, setFileTree] = useState<TreeNode[]>([])
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set())
  const [isTreeLoading, setIsTreeLoading] = useState(false)

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [isChatLoading, setIsChatLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState('gpt-4o')
  const [showModelSelect, setShowModelSelect] = useState(false)
  const chatBottomRef = useRef<HTMLDivElement>(null)
  const chatInputRef = useRef<HTMLTextAreaElement>(null)

  const [rightPanelWidth, setRightPanelWidth] = useState(400)
  const isDragging = useRef(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const [recentPaths, setRecentPaths] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem('abaqusgpt-recent-paths') || '[]') } catch { return [] }
  })
  const [showRecentPaths, setShowRecentPaths] = useState(false)

  // Resize
  const handleDividerMouseDown = useCallback((e: React.MouseEvent) => {
    isDragging.current = true; e.preventDefault()
  }, [])

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging.current || !containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      setRightPanelWidth(Math.max(280, Math.min(720, rect.right - e.clientX)))
    }
    const onMouseUp = () => { isDragging.current = false }
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
    return () => { document.removeEventListener('mousemove', onMouseMove); document.removeEventListener('mouseup', onMouseUp) }
  }, [])

  // Workspace
  const fetchTree = async (p: string) => {
    setIsTreeLoading(true)
    try {
      const resp = await fetch(`/api/v1/workspace/tree?path=${encodeURIComponent(p)}`)
      if (resp.ok) {
        const data = await resp.json()
        setFileTree(data.tree || [])
      }
    } catch { /* ignore */ }
    finally { setIsTreeLoading(false) }
  }

  const openWorkspace = async (path?: string) => {
    const p = (path ?? workspacePath).trim()
    if (!p) return
    if (path) setWorkspacePath(path)
    setIsLoading(true)
    try {
      const response = await fetch('/api/v1/workspace/open', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: p, watch: true }),
      })
      if (!response.ok) { const err = await response.json(); throw new Error(err.detail || '打开目录失败') }
      const data = await response.json()
      setWorkspaceStatus(data.status)
      fetchTree(p)
      const newPaths = [p, ...recentPaths.filter(r => r !== p)].slice(0, 8)
      setRecentPaths(newPaths)
      localStorage.setItem('abaqusgpt-recent-paths', JSON.stringify(newPaths))
    } catch (error) { alert(error instanceof Error ? error.message : '打开目录失败') }
    finally { setIsLoading(false) }
  }

  const refreshStatus = useCallback(async () => {
    if (!workspacePath.trim()) return
    try {
      const response = await fetch(`/api/v1/workspace/status?path=${encodeURIComponent(workspacePath)}`)
      if (response.ok) { const data = await response.json(); setWorkspaceStatus(data) }
    } catch {}
    // Also refresh tree silently
    try {
      const treeResp = await fetch(`/api/v1/workspace/tree?path=${encodeURIComponent(workspacePath)}`)
      if (treeResp.ok) { const td = await treeResp.json(); setFileTree(td.tree || []) }
    } catch {}
  }, [workspacePath])

  useEffect(() => {
    if (autoRefresh && workspaceStatus) { refreshIntervalRef.current = setInterval(refreshStatus, 3000) }
    else if (refreshIntervalRef.current) clearInterval(refreshIntervalRef.current)
    return () => { if (refreshIntervalRef.current) clearInterval(refreshIntervalRef.current) }
  }, [autoRefresh, workspaceStatus, refreshStatus])

  // Directory tree helpers
  const toggleDir = useCallback((dirPath: string) => {
    setExpandedDirs(prev => {
      const next = new Set(prev)
      next.has(dirPath) ? next.delete(dirPath) : next.add(dirPath)
      return next
    })
  }, [])

  const openTreeFile = async (node: TreeNode) => {
    const tabKey = node.path
    setActiveTabName(tabKey)
    if (openTabs.has(tabKey)) return
    const fakeFileInfo: FileInfo = {
      name: node.name,
      path: node.path,
      extension: node.extension || '',
      size: node.size || 0,
      modified: new Date().toISOString(),
      category: 'other',
      type_name: '',
      is_running: !!node.is_running,
    }
    setOpenTabs(prev => { const n = new Map(prev); n.set(tabKey, { file: fakeFileInfo, content: '', isLoading: true, isTruncated: false }); return n })
    try {
      const response = await fetch(`/api/v1/workspace/file/${encodeURIComponent(node.path)}?workspace=${encodeURIComponent(workspacePath)}&tail=0`)
      const data = response.ok ? await response.json() : null
      const content: string = data?.content || (response.ok ? '' : '无法加载文件内容')
      setOpenTabs(prev => { const n = new Map(prev); n.set(tabKey, { file: fakeFileInfo, content, isLoading: false, isTruncated: data?.truncated ?? false }); return n })
    } catch {
      setOpenTabs(prev => { const n = new Map(prev); n.set(tabKey, { file: fakeFileInfo, content: '加载时出错', isLoading: false, isTruncated: false }); return n })
    }
  }

  // Context menu state
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null)
  const [clipboard, setClipboard] = useState<TreeNode | null>(null)
  const [renamingNode, setRenamingNode] = useState<TreeNode | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const contextMenuRef = useRef<HTMLDivElement>(null)
  // Custom dialog state (replaces confirm/prompt which may be blocked)
  const [deleteConfirmNode, setDeleteConfirmNode] = useState<TreeNode | null>(null)
  const [inputDialog, setInputDialog] = useState<{ type: 'file' | 'folder'; dir: string } | null>(null)
  const [inputDialogValue, setInputDialogValue] = useState('')
  const [toastMsg, setToastMsg] = useState<string | null>(null)

  // Close context menu on click outside
  useEffect(() => {
    const handler = () => setContextMenu(null)
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [])

  const handleTreeContextMenu = useCallback((e: React.MouseEvent, node: TreeNode) => {
    e.preventDefault()
    e.stopPropagation()
    setContextMenu({ x: e.clientX, y: e.clientY, node })
  }, [])

  const showToast = (msg: string) => {
    setToastMsg(msg)
    setTimeout(() => setToastMsg(null), 3000)
  }

  const fileOp = async (action: string, body: Record<string, string>) => {
    try {
      const resp = await fetch(`/api/v1/workspace/file-ops/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace: workspacePath, ...body }),
      })
      if (!resp.ok) {
        const err = await resp.json()
        showToast(err.detail || '操作失败')
        return false
      }
      return true
    } catch {
      showToast('操作失败: 网络错误')
      return false
    }
  }

  const handleRename = async (node: TreeNode) => {
    setContextMenu(null)
    setRenamingNode(node)
    setRenameValue(node.name)
  }

  const submitRename = async () => {
    if (!renamingNode || !renameValue.trim() || renameValue === renamingNode.name) {
      setRenamingNode(null)
      return
    }
    const ok = await fileOp('rename', { path: renamingNode.path, new_name: renameValue.trim() })
    if (ok) {
      // Close tab if renamed file was open
      if (openTabs.has(renamingNode.path)) {
        setOpenTabs(prev => { const n = new Map(prev); n.delete(renamingNode.path); return n })
        if (activeTabName === renamingNode.path) setActiveTabName(null)
      }
      fetchTree(workspacePath)
    }
    setRenamingNode(null)
  }

  const handleDelete = (node: TreeNode) => {
    setContextMenu(null)
    setDeleteConfirmNode(node)
  }

  const confirmDelete = async () => {
    if (!deleteConfirmNode) return
    const node = deleteConfirmNode
    setDeleteConfirmNode(null)
    const ok = await fileOp('delete', { path: node.path })
    if (ok) {
      if (openTabs.has(node.path)) {
        setOpenTabs(prev => { const n = new Map(prev); n.delete(node.path); return n })
        if (activeTabName === node.path) setActiveTabName(null)
      }
      showToast(`已删除 ${node.name}`)
      fetchTree(workspacePath)
    }
  }

  const handleCopy = (node: TreeNode) => {
    setContextMenu(null)
    setClipboard(node)
  }

  const handlePaste = async (targetNode: TreeNode) => {
    setContextMenu(null)
    if (!clipboard) return
    const destDir = targetNode.type === 'directory' ? targetNode.path : targetNode.path.split('/').slice(0, -1).join('/') || '.'
    const dest = destDir === '.' ? clipboard.name : `${destDir}/${clipboard.name}`
    const ok = await fileOp('copy', { path: clipboard.path, dest })
    if (ok) fetchTree(workspacePath)
  }

  const handleNewFile = (node: TreeNode) => {
    setContextMenu(null)
    const dir = node.type === 'directory' ? node.path : node.path.split('/').slice(0, -1).join('/') || ''
    setInputDialog({ type: 'file', dir })
    setInputDialogValue('')
  }

  const handleNewFolder = (node: TreeNode) => {
    setContextMenu(null)
    const dir = node.type === 'directory' ? node.path : node.path.split('/').slice(0, -1).join('/') || ''
    setInputDialog({ type: 'folder', dir })
    setInputDialogValue('')
  }

  const submitInputDialog = async () => {
    if (!inputDialog || !inputDialogValue.trim()) { setInputDialog(null); return }
    const name = inputDialogValue.trim()
    const fullPath = inputDialog.dir ? `${inputDialog.dir}/${name}` : name
    if (inputDialog.type === 'file') {
      const ok = await fileOp('new-file', { path: fullPath })
      if (ok) fetchTree(workspacePath)
    } else {
      const ok = await fileOp('new-folder', { path: fullPath })
      if (ok) {
        setExpandedDirs(prev => { const n = new Set(prev); n.add(inputDialog.dir); return n })
        fetchTree(workspacePath)
      }
    }
    setInputDialog(null)
  }

  // File tabs
  const closeTab = (name: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setOpenTabs(prev => { const n = new Map(prev); n.delete(name); return n })
    if (activeTabName === name) {
      const keys = [...openTabs.keys()].filter(k => k !== name)
      setActiveTabName(keys.length > 0 ? keys[keys.length - 1] : null)
    }
  }

  const reloadTab = async () => {
    if (!activeTabName) return
    const tab = openTabs.get(activeTabName); if (!tab) return
    setOpenTabs(prev => { const n = new Map(prev); n.set(activeTabName, { ...tab, isLoading: true }); return n })
    try {
      const response = await fetch(`/api/v1/workspace/file/${encodeURIComponent(activeTabName)}?workspace=${encodeURIComponent(workspacePath)}&tail=0`)
      if (response.ok) { const data = await response.json(); setOpenTabs(prev => { const n = new Map(prev); n.set(activeTabName, { ...tab, content: data.content || '', isLoading: false, isTruncated: data?.truncated ?? false }); return n }) }
    } catch {}
  }

  // Chat
  useEffect(() => { chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [chatMessages])

  const sendMessage = async () => {
    const input = chatInput.trim()
    if (!input || isChatLoading) return
    if (input.startsWith('!')) { setChatInput(''); await executeCommand(input.slice(1).trim()); return }

    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: input, timestamp: new Date() }
    setChatMessages(prev => [...prev, userMsg])
    setChatInput('')
    setIsChatLoading(true)

    const assistantMsgId = (Date.now() + 1).toString()
    let agentSteps: AgentStep[] = []
    let assistantContent = ''

    setChatMessages(prev => [...prev, { id: assistantMsgId, role: 'assistant', content: '', timestamp: new Date(), agentSteps: [] }])

    try {
      const history = chatMessages.filter(m => !m.isCommand).slice(-10).map(m => ({ role: m.role, content: m.content }))
      const response = await fetch('/api/v1/workspace/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input, workspace_path: workspacePath, job_name: workspaceStatus?.jobs?.[0]?.job_name, history, model: selectedModel }),
      })
      if (!response.ok) throw new Error('AI 响应失败')

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      if (reader) {
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n'); buffer = lines.pop() || ''
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'step') {
                agentSteps = [...agentSteps, data as AgentStep]
                setChatMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, agentSteps } : m))
              } else if (data.type === 'content' || data.content) {
                assistantContent += data.content || ''
                setChatMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, content: assistantContent } : m))
              } else if (data.type === 'done' || data.done) {
                setIsChatLoading(false)
              } else if (data.type === 'error' || data.error) {
                setChatMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, content: `错误: ${data.error || '未知错误'}` } : m))
                setIsChatLoading(false)
              }
            } catch { /* skip */ }
          }
        }
      }
    } catch (error) {
      setChatMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, content: `抱歉，发生错误: ${error instanceof Error ? error.message : String(error)}` } : m))
    } finally { setIsChatLoading(false) }
  }

  const executeCommand = async (cmd: string) => {
    setChatMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', content: `$ ${cmd}`, timestamp: new Date(), isCommand: true }])
    setIsChatLoading(true)
    try {
      const response = await fetch('/api/v1/workspace/execute', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd, working_dir: workspacePath, timeout: 60 }),
      })
      const data = await response.json()
      setChatMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(), role: 'assistant', timestamp: new Date(), isCommand: true,
        content: `命令完成 (退出码: ${data.return_code ?? 'N/A'})`,
        commandResult: { stdout: data.stdout, stderr: data.stderr, return_code: data.return_code },
      }])
      setTimeout(refreshStatus, 1000)
    } catch (error) {
      setChatMessages(prev => [...prev, { id: (Date.now() + 1).toString(), role: 'assistant', content: `执行失败: ${error}`, timestamp: new Date(), isCommand: true }])
    } finally { setIsChatLoading(false) }
  }

  const activeTab = activeTabName ? openTabs.get(activeTabName) : null
  const tabsArray = [...openTabs.entries()]

  return (
    <div className="h-full flex flex-col overflow-hidden" ref={containerRef}>

      {/* Context Menu */}
      {contextMenu && (
        <div
          ref={contextMenuRef}
          className="fixed z-50 bg-[#1f1f1f] border border-[#454545] rounded-md shadow-xl py-1 min-w-[180px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={e => e.stopPropagation()}
        >
          {contextMenu.node.type === 'file' && (
            <button className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-[#cccccc] hover:bg-[#094771] transition-colors"
              onClick={() => { setContextMenu(null); openTreeFile(contextMenu.node) }}>
              <Eye className="w-3.5 h-3.5 text-dark-500" /> 打开文件
            </button>
          )}
          <button className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-[#cccccc] hover:bg-[#094771] transition-colors"
            onClick={() => handleRename(contextMenu.node)}>
            <Pencil className="w-3.5 h-3.5 text-dark-500" /> 重命名
          </button>
          <button className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-[#cccccc] hover:bg-[#094771] transition-colors"
            onClick={() => handleCopy(contextMenu.node)}>
            <Copy className="w-3.5 h-3.5 text-dark-500" /> 复制
          </button>
          {clipboard && (
            <button className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-[#cccccc] hover:bg-[#094771] transition-colors"
              onClick={() => handlePaste(contextMenu.node)}>
              <ClipboardPaste className="w-3.5 h-3.5 text-dark-500" /> 粘贴
              <span className="ml-auto text-[10px] text-dark-600 truncate max-w-[60px]">{clipboard.name}</span>
            </button>
          )}
          <div className="border-t border-[#454545] my-1" />
          <button className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-[#cccccc] hover:bg-[#094771] transition-colors"
            onClick={() => handleNewFile(contextMenu.node)}>
            <FilePlus className="w-3.5 h-3.5 text-dark-500" /> 新建文件
          </button>
          <button className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-[#cccccc] hover:bg-[#094771] transition-colors"
            onClick={() => handleNewFolder(contextMenu.node)}>
            <FolderPlus className="w-3.5 h-3.5 text-dark-500" /> 新建文件夹
          </button>
          <div className="border-t border-[#454545] my-1" />
          <button className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-red-400 hover:bg-[#094771] transition-colors"
            onClick={() => handleDelete(contextMenu.node)}>
            <Trash2 className="w-3.5 h-3.5" /> 删除
          </button>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {deleteConfirmNode && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50" onClick={() => setDeleteConfirmNode(null)}>
          <div className="bg-[#1e1e1e] border border-[#454545] rounded-lg shadow-2xl p-5 min-w-[320px] max-w-[400px]" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0" />
              <span className="text-sm text-white font-medium">确认删除</span>
            </div>
            <p className="text-xs text-[#cccccc] mb-4 leading-relaxed">
              确定要删除{deleteConfirmNode.type === 'directory' ? '文件夹' : '文件'} <strong className="text-white">"{deleteConfirmNode.name}"</strong>
              {deleteConfirmNode.type === 'directory' ? ' 及其所有内容' : ''} 吗？<br/>
              <span className="text-red-400">此操作不可恢复。</span>
            </p>
            <div className="flex justify-end gap-2">
              <button className="px-3 py-1.5 text-xs text-[#cccccc] bg-[#3c3c3c] hover:bg-[#505050] rounded transition-colors"
                onClick={() => setDeleteConfirmNode(null)}>取消</button>
              <button className="px-3 py-1.5 text-xs text-white bg-red-600 hover:bg-red-700 rounded transition-colors"
                onClick={confirmDelete}>删除</button>
            </div>
          </div>
        </div>
      )}

      {/* New File/Folder Input Dialog */}
      {inputDialog && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50" onClick={() => setInputDialog(null)}>
          <div className="bg-[#1e1e1e] border border-[#454545] rounded-lg shadow-2xl p-5 min-w-[320px]" onClick={e => e.stopPropagation()}>
            <p className="text-sm text-white font-medium mb-3">
              {inputDialog.type === 'file' ? '新建文件' : '新建文件夹'}
            </p>
            <input
              autoFocus
              className="w-full bg-[#3c3c3c] border border-[#606060] focus:border-primary-500 rounded px-3 py-1.5 text-xs text-white font-mono outline-none mb-4"
              placeholder={inputDialog.type === 'file' ? '输入文件名...' : '输入文件夹名...'}
              value={inputDialogValue}
              onChange={e => setInputDialogValue(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') submitInputDialog(); if (e.key === 'Escape') setInputDialog(null) }}
            />
            <div className="flex justify-end gap-2">
              <button className="px-3 py-1.5 text-xs text-[#cccccc] bg-[#3c3c3c] hover:bg-[#505050] rounded transition-colors"
                onClick={() => setInputDialog(null)}>取消</button>
              <button className="px-3 py-1.5 text-xs text-white bg-primary-600 hover:bg-primary-700 rounded transition-colors"
                onClick={submitInputDialog}>确定</button>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[70] bg-[#1e1e1e] border border-[#454545] rounded-lg shadow-2xl px-4 py-2.5 text-xs text-[#cccccc] animate-pulse">
          {toastMsg}
        </div>
      )}

      {/* Header */}
      <div className="flex-shrink-0 px-4 py-2.5 border-b border-dark-700 flex items-center gap-2 bg-dark-900">
        <HardDrive className="w-4 h-4 text-primary-400 flex-shrink-0" />
        <div className="relative flex-1">
          <input
            type="text" value={workspacePath}
            onChange={e => setWorkspacePath(e.target.value)}
            onFocus={() => setShowRecentPaths(true)}
            onBlur={() => setTimeout(() => setShowRecentPaths(false), 200)}
            placeholder="输入 Abaqus 工作目录路径..."
            className="w-full bg-dark-800 border border-dark-600 rounded-lg px-4 py-1.5 text-sm focus:outline-none focus:border-primary-500"
            onKeyDown={e => e.key === 'Enter' && openWorkspace()}
          />
          {showRecentPaths && recentPaths.length > 0 && (
            <div className="absolute top-full left-0 right-0 bg-dark-800 border border-dark-600 rounded-lg mt-1 z-50 shadow-xl overflow-hidden">
              <div className="px-3 py-1.5 text-xs text-dark-500 flex items-center gap-1 border-b border-dark-700">
                <History className="w-3 h-3" /> 最近打开
              </div>
              {recentPaths.map((p, i) => (
                <button key={i} className="w-full text-left px-4 py-1.5 text-xs font-mono text-dark-300 hover:bg-dark-700 hover:text-white border-b border-dark-700 last:border-0 transition-colors"
                  onMouseDown={() => { setWorkspacePath(p); openWorkspace(p) }}>{p}</button>
              ))}
            </div>
          )}
        </div>
        <button onClick={() => openWorkspace()} disabled={isLoading || !workspacePath.trim()}
          className="px-3 py-1.5 bg-primary-600 hover:bg-primary-500 disabled:bg-dark-700 rounded-lg flex items-center gap-2 text-sm flex-shrink-0">
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FolderOpen className="w-4 h-4" />} 打开
        </button>
        {workspaceStatus && (<>
          <button onClick={refreshStatus} className="p-1.5 bg-dark-700 hover:bg-dark-600 rounded-lg flex-shrink-0" title="刷新">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button onClick={() => setAutoRefresh(!autoRefresh)}
            className={`p-1.5 rounded-lg flex-shrink-0 ${autoRefresh ? 'bg-emerald-600' : 'bg-dark-700 hover:bg-dark-600'}`}
            title={autoRefresh ? '关闭自动刷新' : '开启自动刷新 (3秒)'}>
            <Zap className="w-4 h-4" />
          </button>
        </>)}
      </div>

      {workspaceStatus ? (
        <div className="flex-1 flex overflow-hidden">

          {/* Left: Jobs & Files (fixed 256px) */}
          <div className="w-64 flex-shrink-0 border-r border-dark-700 flex flex-col overflow-hidden bg-dark-900">
            <div className="flex-shrink-0 p-3 border-b border-dark-700">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-dark-400 uppercase tracking-widest">作业状态</span>
                <span className="text-xs text-dark-600 font-mono">{workspaceStatus.last_update?.slice(11, 19)}</span>
              </div>
              {workspaceStatus.jobs.length === 0 ? (
                <p className="text-xs text-dark-600 italic">未检测到作业</p>
              ) : workspaceStatus.jobs.map(job => (
                <div key={job.job_name} className="mb-1">
                  <div className="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-dark-800"
                    onClick={() => setExpandedJobs(prev => { const n = new Set(prev); n.has(job.job_name) ? n.delete(job.job_name) : n.add(job.job_name); return n })}>
                    <span className={getStatusColor(job.status)}>{getStatusIcon(job.status)}</span>
                    <span className="flex-1 text-xs font-mono truncate text-dark-300">{job.job_name}</span>
                    {expandedJobs.has(job.job_name) ? <ChevronDown className="w-3 h-3 text-dark-600" /> : <ChevronRight className="w-3 h-3 text-dark-600" />}
                  </div>
                  {expandedJobs.has(job.job_name) && (
                    <div className="pl-7 pb-1 text-xs space-y-0.5">
                      {job.current_step && <div className="text-dark-500">Step {job.current_step}, Inc {job.current_increment}</div>}
                      {job.errors.length > 0 && <div className="text-red-500">{job.errors.length} 个错误</div>}
                      {job.warnings.length > 0 && <div className="text-yellow-500">{job.warnings.length} 个警告</div>}
                      {job.last_message && <div className="text-dark-600 truncate" title={job.last_message}>{job.last_message}</div>}
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="flex-1 overflow-y-auto">
              <div className="flex items-center justify-between px-3 pt-3 pb-1">
                <span className="text-xs font-semibold text-dark-400 uppercase tracking-widest">资源管理器</span>
                <button onClick={() => fetchTree(workspacePath)} className="p-0.5 hover:bg-dark-700 rounded" title="刷新目录树">
                  <RefreshCw className={`w-3 h-3 text-dark-500 ${isTreeLoading ? 'animate-spin' : ''}`} />
                </button>
              </div>
              {fileTree.length === 0 ? (
                <p className="text-xs text-dark-600 italic px-3 py-2">暂无文件</p>
              ) : (
                <div className="pb-2">
                  {fileTree.map(node => (
                    <FileTreeNodeView
                      key={node.path}
                      node={node}
                      depth={0}
                      expandedDirs={expandedDirs}
                      toggleDir={toggleDir}
                      onFileClick={openTreeFile}
                      activeFilePath={activeTabName}
                      onContextMenu={handleTreeContextMenu}
                      renamingPath={renamingNode?.path ?? null}
                      renameValue={renameValue}
                      onRenameChange={setRenameValue}
                      onRenameSubmit={submitRename}
                      onRenameCancel={() => setRenamingNode(null)}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Center: File viewer (flexible) */}
          <div className="flex-1 flex flex-col overflow-hidden min-w-0">
            {tabsArray.length > 0 ? (
              <div className="flex-shrink-0 flex items-end bg-[#252526] border-b border-[#3c3c3c] overflow-x-auto">
                {tabsArray.map(([name, tab]) => (
                  <div key={name} onClick={() => setActiveTabName(name)}
                    className={`group flex items-center gap-1.5 px-4 py-2 cursor-pointer border-r border-[#3c3c3c] text-xs font-mono flex-shrink-0 max-w-[160px] transition-colors ${
                      activeTabName === name ? 'bg-[#1e1e1e] text-white border-t-2 border-t-primary-500' : 'text-[#858585] hover:bg-[#2d2d2d] hover:text-[#ccc]'}`}>
                    <FileText className={`w-3 h-3 flex-shrink-0 ${getFileColor(tab.file.extension, tab.file.is_running)}`} />
                    {tab.isLoading && <Loader2 className="w-3 h-3 animate-spin text-primary-400 flex-shrink-0" />}
                    <span className="truncate" title={name}>{name.includes('/') ? name.split('/').pop() : name}</span>
                    <button onClick={e => closeTab(name, e)}
                      className={`flex-shrink-0 hover:text-red-400 ml-1 opacity-0 group-hover:opacity-100 transition-opacity ${activeTabName === name ? 'opacity-40' : ''}`}>
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
                {activeTab && (
                  <button onClick={reloadTab} className="ml-auto px-3 py-2 text-[#858585] hover:text-white flex-shrink-0" title="刷新文件">
                    <RefreshCw className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ) : (
              <div className="flex-shrink-0 h-8 bg-[#252526] border-b border-[#3c3c3c]" />
            )}
            {activeTab ? (
              <div className="flex-1 overflow-hidden">
                <CodeViewer content={activeTab.content} filename={activeTab.file.name} isLoading={activeTab.isLoading} isTruncated={activeTab.isTruncated} />
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center bg-[#1e1e1e] text-[#555]">
                <div className="text-center">
                  <Eye className="w-10 h-10 mx-auto mb-3 opacity-20" />
                  <p className="text-sm">点击左侧文件打开查看</p>
                  <p className="text-xs mt-1 opacity-50">支持行号显示 · 语法高亮 · 跳转行</p>
                </div>
              </div>
            )}
          </div>

          {/* Resize handle */}
          <ResizeHandle onMouseDown={handleDividerMouseDown} />

          {/* Right: AI Chat (resizable) */}
          <div className="flex-shrink-0 flex flex-col border-l border-dark-700 bg-dark-900 overflow-hidden" style={{ width: rightPanelWidth }}>
            {/* Header */}
            <div className="flex-shrink-0 flex items-center gap-2 px-3 py-2 border-b border-dark-700 bg-dark-800">
              <Bot className="w-4 h-4 text-primary-400" />
              <span className="text-sm font-semibold flex-1">AI 智能体</span>
              <div className="relative">
                <button onClick={() => setShowModelSelect(!showModelSelect)}
                  onBlur={() => setTimeout(() => setShowModelSelect(false), 200)}
                  className="flex items-center gap-1.5 px-2 py-1 bg-dark-700 hover:bg-dark-600 rounded text-xs text-dark-300 hover:text-white">
                  <Cpu className="w-3 h-3" />
                  <span className="max-w-[90px] truncate font-mono">{AVAILABLE_MODELS.find(m => m.id === selectedModel)?.label ?? selectedModel}</span>
                  <ChevronDown className="w-3 h-3 opacity-50" />
                </button>
                {showModelSelect && (
                  <div className="absolute top-full right-0 bg-dark-800 border border-dark-600 rounded-lg mt-1 z-50 w-52 shadow-2xl overflow-hidden">
                    {AVAILABLE_MODELS.map(model => (
                      <button key={model.id} onClick={() => { setSelectedModel(model.id); setShowModelSelect(false) }}
                        className={`w-full text-left px-3 py-2 text-xs hover:bg-dark-700 flex items-center justify-between ${selectedModel === model.id ? 'text-primary-400 bg-primary-900/20' : 'text-dark-300'}`}>
                        <span>{model.label}</span>
                        <span className={`text-xs ${model.color} opacity-70`}>{model.badge}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Quick chips */}
            <div className="flex-shrink-0 flex gap-1 px-3 py-2 border-b border-dark-700 flex-wrap bg-dark-900/60">
              {QUICK_QUESTIONS.map(({ label, q }) => (
                <button key={label} onClick={() => { setChatInput(q); chatInputRef.current?.focus() }}
                  className="px-2 py-0.5 text-xs bg-dark-800 hover:bg-dark-700 border border-dark-700 rounded-full text-dark-400 hover:text-white transition-colors">
                  {label}
                </button>
              ))}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4">
              {chatMessages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center py-8">
                  <div className="w-12 h-12 rounded-2xl bg-primary-900/30 border border-primary-800/30 flex items-center justify-center mb-4">
                    <Bot className="w-6 h-6 text-primary-400" />
                  </div>
                  <p className="text-sm font-medium text-dark-400">AbaqusGPT 智能体</p>
                  <p className="text-xs text-dark-600 mt-1.5 leading-relaxed max-w-[180px]">自动读取文件、分析仿真、透明展示工具调用过程</p>
                  <div className="mt-5 w-full space-y-2">
                    {[
                      { icon: '🔍', text: '自动检测意图并读取相关文件' },
                      { icon: '📊', text: '分析 MSG / STA / DAT 输出' },
                      { icon: '🔧', text: '收敛参数调优与修改建议' },
                      { icon: '🤖', text: `当前: ${AVAILABLE_MODELS.find(m => m.id === selectedModel)?.label ?? selectedModel}` },
                      { icon: '⚡', text: '输入 !命令 直接执行 Abaqus' },
                    ].map(({ icon, text }, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs text-dark-600 text-left">
                        <span className="flex-shrink-0">{icon}</span><span className="leading-relaxed">{text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : chatMessages.map(msg => (
                <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  {msg.role === 'assistant' && msg.agentSteps && msg.agentSteps.length > 0 && (
                    <div className="w-full mb-1"><AgentSteps steps={msg.agentSteps} /></div>
                  )}
                  <div className={`max-w-[92%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                    msg.role === 'user'
                      ? msg.isCommand ? 'bg-emerald-900/30 text-emerald-300 font-mono border border-emerald-800/30' : 'bg-primary-600 text-white'
                      : 'bg-dark-800 text-dark-200 border border-dark-700'}`}>
                    {msg.isCommand && msg.role === 'user' && (
                      <div className="flex items-center gap-1 text-emerald-400/70 text-xs mb-1">
                        <Terminal className="w-3 h-3" /><span>命令执行</span>
                      </div>
                    )}
                    {msg.content ? (
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                    ) : msg.role === 'assistant' ? (
                      <div className="flex items-center gap-2 text-dark-500">
                        <Loader2 className="w-3 h-3 animate-spin" /><span>思考中...</span>
                      </div>
                    ) : null}
                    {msg.commandResult && (
                      <div className="mt-2 p-2 bg-dark-950 rounded text-xs font-mono border border-dark-700 max-h-32 overflow-y-auto">
                        {msg.commandResult.stdout && <pre className="text-dark-300 whitespace-pre-wrap">{msg.commandResult.stdout}</pre>}
                        {msg.commandResult.stderr && <pre className="text-red-400 whitespace-pre-wrap">{msg.commandResult.stderr}</pre>}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={chatBottomRef} />
            </div>

            {/* Input */}
            <div className="flex-shrink-0 p-3 border-t border-dark-700 bg-dark-800">
              <div className="flex gap-2 items-end">
                <textarea
                  ref={chatInputRef} value={chatInput} onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
                  placeholder="问 Abaqus 问题，或 !命令 执行..." rows={2} disabled={isChatLoading}
                  className="flex-1 bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 text-xs resize-none focus:outline-none focus:border-primary-500 disabled:opacity-40 min-h-[52px] max-h-32"
                />
                <button onClick={sendMessage} disabled={isChatLoading || !chatInput.trim()}
                  className="p-2.5 bg-primary-600 hover:bg-primary-500 disabled:bg-dark-700 rounded-lg flex-shrink-0 self-end">
                  {isChatLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-dark-600 mt-1.5">Enter 发送 · Shift+Enter 换行 · <code className="bg-dark-700 px-0.5 rounded text-dark-400">!</code> 执行命令</p>
            </div>
          </div>

        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center bg-[#1e1e1e]">
          <div className="text-center max-w-lg px-6">
            <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-dark-800 border border-dark-700 flex items-center justify-center">
              <HardDrive className="w-8 h-8 text-dark-600" />
            </div>
            <h3 className="text-lg font-semibold text-dark-300 mb-2">打开 Abaqus 工作目录</h3>
            <p className="text-sm text-dark-500 mb-6">输入目录路径，开始智能监控和 AI 辅助诊断</p>
            {recentPaths.length > 0 && (
              <div className="text-left bg-dark-900 rounded-xl overflow-hidden mb-5 border border-dark-700">
                <div className="px-4 py-2 text-xs text-dark-500 border-b border-dark-700 flex items-center gap-1">
                  <History className="w-3 h-3" /> 最近打开
                </div>
                {recentPaths.slice(0, 5).map((p, i) => (
                  <button key={i} onClick={() => { setWorkspacePath(p); openWorkspace(p) }}
                    className="w-full text-left px-4 py-2.5 text-xs font-mono text-dark-400 hover:bg-dark-800 hover:text-white border-b border-dark-700 last:border-0 transition-colors truncate">
                    {p}
                  </button>
                ))}
              </div>
            )}
            <div className="text-left bg-dark-900 rounded-xl p-4 border border-dark-700 space-y-2.5">
              {[
                { icon: '🔢', text: 'VSCode 风格行号显示 + 语法高亮（INP/MSG/STA）' },
                { icon: '📑', text: '多标签页同时打开多个文件' },
                { icon: '↔️', text: '拖拽调整代码区与对话区的宽度' },
                { icon: '🤖', text: 'AI 智能体透明展示：读了哪些文件、调用了什么模型' },
                { icon: '🔄', text: '支持 GPT-4o / Claude / DeepSeek 多模型切换' },
                { icon: '⚡', text: '!命令 直接执行 Abaqus · 3秒自动刷新监控' },
              ].map(({ icon, text }, i) => (
                <div key={i} className="flex items-start gap-3 text-xs text-dark-500">
                  <span className="flex-shrink-0 text-base leading-none">{icon}</span>
                  <span className="leading-relaxed">{text}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
