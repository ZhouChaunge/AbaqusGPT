import { useState, useEffect } from 'react'
import { ChevronDown } from 'lucide-react'

interface ModelInfo {
  id: string
  name: string
  provider: string
  provider_name: string
  group: string
}

interface ModelSelectorProps {
  value: string
  onChange: (model: string) => void
}

export default function ModelSelector({ value, onChange }: ModelSelectorProps) {
  const [models, setModels] = useState<ModelInfo[]>([])
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    fetchModels()
  }, [])

  const fetchModels = async () => {
    try {
      const res = await fetch('/api/v1/models/')
      if (res.ok) {
        const data = await res.json()
        setModels(data.models)
        // If current value not in available models, use active_model from server
        if (data.active_model && !data.models.find((m: ModelInfo) => m.id === value)) {
          onChange(data.active_model)
        }
      }
    } catch {
      // Ignore
    }
  }

  const currentModel = models.find((m) => m.id === value)

  // Group models by group
  const grouped = models.reduce<Record<string, ModelInfo[]>>((acc, m) => {
    const key = m.group
    if (!acc[key]) acc[key] = []
    acc[key].push(m)
    return acc
  }, {})

  const groupLabels: Record<string, string> = {
    international: '🌍 国际模型',
    chinese: '🇨🇳 国产模型',
    local: '💻 本地模型',
  }

  const handleSelect = async (modelId: string) => {
    onChange(modelId)
    setIsOpen(false)
    // Persist selection to backend
    try {
      await fetch('/api/v1/models/active', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: modelId }),
      })
    } catch {
      // Ignore
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-dark-800 hover:bg-dark-700 rounded-lg text-sm transition-colors border border-dark-700"
      >
        <span className="text-dark-300 max-w-[140px] truncate">
          {currentModel ? currentModel.name : value}
        </span>
        <ChevronDown className={`w-3.5 h-3.5 text-dark-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-50 w-64 max-h-80 overflow-y-auto bg-dark-800 border border-dark-700 rounded-lg shadow-xl">
            {Object.entries(grouped).map(([group, groupModels]) => (
              <div key={group}>
                <div className="px-3 py-1.5 text-xs font-medium text-dark-400 bg-dark-900/50 sticky top-0">
                  {groupLabels[group] || group}
                </div>
                {groupModels.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => handleSelect(m.id)}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-dark-700 transition-colors flex items-center justify-between ${
                      m.id === value ? 'text-primary-400 bg-dark-700/50' : 'text-dark-200'
                    }`}
                  >
                    <span>{m.name}</span>
                    <span className="text-xs text-dark-500">{m.provider_name}</span>
                  </button>
                ))}
              </div>
            ))}
            {models.length === 0 && (
              <div className="px-3 py-4 text-sm text-dark-400 text-center">
                暂无可用模型，请先配置 API Key
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
