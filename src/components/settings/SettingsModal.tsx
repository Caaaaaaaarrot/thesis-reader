import { useSettingsStore } from '../../stores/settings'
import { useState } from 'react'

interface Props {
  open: boolean
  onClose: () => void
}

export default function SettingsModal({ open, onClose }: Props) {
  const aiSettings = useSettingsStore((s) => s.aiSettings)
  const setAISettings = useSettingsStore((s) => s.setAISettings)
  const [showKey, setShowKey] = useState(false)

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative bg-white rounded-lg shadow-xl w-[480px] max-h-[80vh] overflow-auto">
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200">
          <h2 className="text-sm font-semibold text-gray-700">设置</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-sm">
            ✕
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          {/* AI Provider */}
          <div>
            <div className="text-xs font-semibold text-gray-400 uppercase mb-3">AI 服务配置</div>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">API 地址</label>
                <input
                  type="text"
                  defaultValue={aiSettings.endpoint}
                  placeholder="https://api.openai.com/v1"
                  onBlur={(e) => setAISettings({ endpoint: e.target.value })}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-400"
                />
                <p className="text-[10px] text-gray-400 mt-0.5">
                  任何兼容 OpenAI 接口的地址，如 https://api.openai.com/v1
                </p>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">API Key</label>
                <div className="flex gap-1">
                  <input
                    type={showKey ? 'text' : 'password'}
                    defaultValue={aiSettings.apiKey}
                    placeholder="sk-..."
                    onBlur={(e) => setAISettings({ apiKey: e.target.value })}
                    className="flex-1 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-400"
                  />
                  <button
                    onClick={() => setShowKey(!showKey)}
                    className="px-2 text-xs text-gray-400 hover:text-gray-600 border border-gray-200 rounded"
                  >
                    {showKey ? '隐藏' : '显示'}
                  </button>
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">模型名称</label>
                <input
                  type="text"
                  defaultValue={aiSettings.model}
                  onBlur={(e) => setAISettings({ model: e.target.value })}
                  className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-400"
                />
                <p className="text-[10px] text-gray-400 mt-0.5">
                  支持多模态的模型效果更佳，如 gpt-4o, claude-sonnet-4-6 等
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-100 px-5 py-3 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  )
}
