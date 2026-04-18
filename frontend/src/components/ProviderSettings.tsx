import { useState, useEffect } from 'react'
import { X, Plus, Trash2, CheckCircle, XCircle, Loader2, Key } from 'lucide-react'

interface ProviderKeyInfo {
  id: string
  provider: string
  provider_name: string
  group: string
  masked_key: string
  label: string
  test_status: string | null
  test_latency_ms: number | null
  created_at: string
}

interface CatalogItem {
  id: string
  name: string
  group: string
  models: string[]
  configured: boolean
  key_count: number
}

interface ProviderSettingsProps {
  isOpen: boolean
  onClose: () => void
}

export default function ProviderSettings({ isOpen, onClose }: ProviderSettingsProps) {
  const [catalog, setCatalog] = useState<CatalogItem[]>([])
  const [keys, setKeys] = useState<ProviderKeyInfo[]>([])
  const [addingFor, setAddingFor] = useState<string | null>(null)
  const [newKey, setNewKey] = useState('')
  const [newLabel, setNewLabel] = useState('')
  const [testing, setTesting] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      fetchData()
    }
  }, [isOpen])

  const fetchData = async () => {
    try {
      const [catalogRes, keysRes] = await Promise.all([
        fetch('/api/v1/providers/catalog'),
        fetch('/api/v1/providers/keys'),
      ])
      if (catalogRes.ok) setCatalog(await catalogRes.json())
      if (keysRes.ok) setKeys(await keysRes.json())
    } catch {
      // Ignore
    }
  }

  const handleAddKey = async (provider: string) => {
    if (!newKey.trim()) return
    try {
      const res = await fetch('/api/v1/providers/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          api_key: newKey.trim(),
          label: newLabel.trim() || null,
        }),
      })
      if (res.ok) {
        setNewKey('')
        setNewLabel('')
        setAddingFor(null)
        await fetchData()
      }
    } catch {
      // Ignore
    }
  }

  const handleDeleteKey = async (keyId: string) => {
    try {
      await fetch(`/api/v1/providers/keys/${keyId}`, { method: 'DELETE' })
      await fetchData()
    } catch {
      // Ignore
    }
  }

  const handleTestKey = async (keyId: string) => {
    setTesting(keyId)
    try {
      const res = await fetch(`/api/v1/providers/keys/${keyId}/test`, {
        method: 'POST',
      })
      if (res.ok) {
        await fetchData()
      }
    } catch {
      // Ignore
    } finally {
      setTesting(null)
    }
  }

  if (!isOpen) return null

  const groupLabels: Record<string, string> = {
    international: '🌍 国际模型',
    chinese: '🇨🇳 国产模型',
    local: '💻 本地模型',
  }

  const groupOrder = ['international', 'chinese', 'local']

  const grouped = groupOrder.map((g) => ({
    group: g,
    label: groupLabels[g],
    providers: catalog.filter((c) => c.group === g),
  }))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-dark-900 border border-dark-700 rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-dark-800">
          <div className="flex items-center gap-2">
            <Key className="w-5 h-5 text-primary-400" />
            <h2 className="text-lg font-semibold">LLM 模型设置</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-dark-800 transition-colors"
          >
            <X className="w-5 h-5 text-dark-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {grouped.map(({ group, label, providers }) => (
            <div key={group}>
              <h3 className="text-sm font-medium text-dark-400 mb-3">{label}</h3>
              <div className="space-y-3">
                {providers.map((provider) => {
                  const providerKeys = keys.filter((k) => k.provider === provider.id)
                  return (
                    <div
                      key={provider.id}
                      className="bg-dark-800/50 rounded-lg border border-dark-700 p-4"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <span className="font-medium text-sm">{provider.name}</span>
                          <span className="text-xs text-dark-500 ml-2">
                            {provider.models.join(', ')}
                          </span>
                        </div>
                        {provider.id !== 'ollama' && (
                          <button
                            onClick={() => {
                              setAddingFor(addingFor === provider.id ? null : provider.id)
                              setNewKey('')
                              setNewLabel('')
                            }}
                            className="flex items-center gap-1 text-xs text-primary-400 hover:text-primary-300 transition-colors"
                          >
                            <Plus className="w-3.5 h-3.5" />
                            添加 Key
                          </button>
                        )}
                      </div>

                      {/* Existing keys */}
                      {providerKeys.map((k) => (
                        <div
                          key={k.id}
                          className="flex items-center justify-between py-1.5 pl-2 group"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="text-sm text-dark-300 font-mono truncate">
                              {k.masked_key}
                            </span>
                            {k.label && (
                              <span className="text-xs text-dark-500">({k.label})</span>
                            )}
                          </div>
                          <div className="flex items-center gap-1.5 flex-shrink-0">
                            {/* Test status */}
                            {k.test_status === 'ok' && (
                              <span className="flex items-center gap-1 text-xs text-green-400">
                                <CheckCircle className="w-3.5 h-3.5" />
                                {k.test_latency_ms}ms
                              </span>
                            )}
                            {k.test_status === 'error' && (
                              <span className="flex items-center gap-1 text-xs text-red-400">
                                <XCircle className="w-3.5 h-3.5" />
                                失败
                              </span>
                            )}
                            {/* Test button */}
                            <button
                              onClick={() => handleTestKey(k.id)}
                              disabled={testing === k.id}
                              className="px-2 py-0.5 text-xs bg-dark-700 hover:bg-dark-600 rounded transition-colors disabled:opacity-50"
                            >
                              {testing === k.id ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                '测试'
                              )}
                            </button>
                            {/* Delete button */}
                            <button
                              onClick={() => handleDeleteKey(k.id)}
                              className="p-1 text-dark-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      ))}

                      {providerKeys.length === 0 && provider.id !== 'ollama' && addingFor !== provider.id && (
                        <p className="text-xs text-dark-500 pl-2">未配置</p>
                      )}

                      {/* Add key form */}
                      {addingFor === provider.id && (
                        <div className="mt-2 flex gap-2">
                          <input
                            type="password"
                            value={newKey}
                            onChange={(e) => setNewKey(e.target.value)}
                            placeholder="输入 API Key..."
                            className="flex-1 px-3 py-1.5 bg-dark-900 border border-dark-600 rounded text-sm focus:outline-none focus:border-primary-500"
                            autoFocus
                          />
                          <input
                            type="text"
                            value={newLabel}
                            onChange={(e) => setNewLabel(e.target.value)}
                            placeholder="备注"
                            className="w-20 px-2 py-1.5 bg-dark-900 border border-dark-600 rounded text-sm focus:outline-none focus:border-primary-500"
                          />
                          <button
                            onClick={() => handleAddKey(provider.id)}
                            disabled={!newKey.trim()}
                            className="px-3 py-1.5 bg-primary-600 hover:bg-primary-500 rounded text-sm transition-colors disabled:opacity-50"
                          >
                            保存
                          </button>
                          <button
                            onClick={() => {
                              setAddingFor(null)
                              setNewKey('')
                              setNewLabel('')
                            }}
                            className="px-2 py-1.5 text-dark-400 hover:text-dark-200 text-sm transition-colors"
                          >
                            取消
                          </button>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
