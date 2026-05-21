import { useSSE } from '../../hooks/useSSE'
import { useState } from 'react'
import { usePapersStore, SpeedReadData } from '../../stores/papers'

type SpeedReadResult = SpeedReadData

interface Props {
  paperId: string
  cachedResult: SpeedReadResult | null
  onGenerated: (result: SpeedReadResult) => void
}

type Phase = 'idle' | 'extracting' | 'scoring' | 'rendering' | 'calling_llm'

const phaseLabels: Record<Phase, string> = {
  idle: '',
  extracting: '正在提取 PDF 文本...',
  scoring: '正在分析页面重要性...',
  rendering: '正在渲染图表...',
  calling_llm: '正在调用 AI 模型进行速读...',
}

export default function SpeedReadView({ paperId, cachedResult, onGenerated }: Props) {
  const { loading, connect, abort } = useSSE()
  const [result, setResult] = useState<Partial<SpeedReadResult> | null>(cachedResult)
  const [error, setError] = useState('')

  const generating = usePapersStore((s) => s.generating)
  const startGenerating = usePapersStore((s) => s.startGenerating)
  const updateGenerating = usePapersStore((s) => s.updateGenerating)
  const finishGenerating = usePapersStore((s) => s.finishGenerating)

  const myState = generating[paperId]
  const isMyGeneration = !!myState
  const otherCount = Object.keys(generating).filter((id) => id !== paperId).length

  // 用 store 里的进度（切换论文后重挂载时不会丢）
  const phase: Phase = myState?.phase || 'idle'
  const fieldData: Record<string, string> = myState?.fields || {}
  const effectiveLoading = loading || (isMyGeneration && myState.phase !== 'idle')

  const displayResult = result || cachedResult

  const handleGenerate = () => {
    const aiSettings = getAISettings()
    if (!aiSettings.apiKey) {
      setError('请先在设置中配置 AI API Key')
      return
    }

    setError('')
    setResult(null)
    startGenerating(paperId)

    connect(
      `/api/speedread/${paperId}?force=true`,
      aiSettings,
      (msg) => {
        switch (msg.event) {
          case 'status': {
            const d = msg.data as { phase: string }
            updateGenerating(paperId, { phase: d.phase as Phase })
            break
          }
          case 'field': {
            const d = msg.data as { field: string; value: string }
            const s = usePapersStore.getState()
            const cur = s.generating[paperId]?.fields || {}
            updateGenerating(paperId, { fields: { ...cur, [d.field]: d.value } })
            break
          }
        }
      },
      () => {
        finishGenerating(paperId)
        fetchCachedResult()
      },
      (errMsg) => {
        setError(errMsg)
        finishGenerating(paperId)
      },
    )
  }

  const fetchCachedResult = async () => {
    try {
      const { getBaseUrl } = await import('../../api/client')
      const resp = await fetch(`${getBaseUrl()}/api/speedread/${paperId}`)
      if (resp.ok) {
        const data = await resp.json()
        if (data.status === 'success') {
          setResult(data.result)
          onGenerated(data.result)
        }
      }
    } catch { /* ignore */ }
  }

  const sr = displayResult

  return (
    <div className="border-t border-gray-200 pt-4 mt-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-purple-600">
          {sr ? 'AI 速读摘要' : 'AI 速读'}
        </h3>
        <div className="flex gap-2">
          {effectiveLoading && isMyGeneration ? (
            <button
              onClick={() => { abort(); finishGenerating(paperId) }}
              className="text-xs px-2 py-1 rounded border border-red-300 text-red-500 hover:bg-red-50"
            >
              取消
            </button>
          ) : (
            <button
              onClick={handleGenerate}
              className="text-xs px-3 py-1 rounded bg-purple-500 text-white hover:bg-purple-600"
            >
              {sr ? '重新生成' : '生成速读'}
            </button>
          )}
        </div>
      </div>

      {/* 其他论文正在生成中 */}
      {otherCount > 0 && !isMyGeneration && (
        <div className="bg-purple-50 border border-purple-100 rounded p-2 mb-3 text-xs text-purple-500 flex items-center gap-2">
          <div className="w-3 h-3 border border-purple-400 border-t-transparent rounded-full animate-spin" />
          {otherCount} 篇论文正在后台生成速读
        </div>
      )}

      {/* 加载中 */}
      {effectiveLoading && isMyGeneration && (
        <div className="flex items-center gap-2 py-8 justify-center">
          <div className="w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-purple-500">{phaseLabels[phase]}</span>
        </div>
      )}

      {/* 流式显示字段 */}
      {effectiveLoading && isMyGeneration && Object.keys(fieldData).length > 0 && (
        <div className="space-y-2 mb-3">
          {Object.entries(fieldData).map(([field, value]) => (
            <div key={field} className="bg-purple-50 rounded p-2">
              <div className="text-[10px] text-purple-400 mb-0.5">{field}</div>
              <p className="text-xs text-gray-700">{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* 错误 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* 完整结果 */}
      {sr && sr.one_sentence && !effectiveLoading && (
        <div className="space-y-3">
          {/* 一句话 */}
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded p-3">
            <div className="text-[10px] font-medium text-purple-400 uppercase mb-1">一句话总结</div>
            <p className="text-sm text-gray-800">{sr.one_sentence}</p>
          </div>

          {/* 关键发现 */}
          {sr.quick_takeaways && sr.quick_takeaways.length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-400 mb-1">关键发现</div>
              <ul className="space-y-1">
                {sr.quick_takeaways.map((t, i) => (
                  <li key={i} className="text-sm text-gray-600 flex gap-1.5">
                    <span className="text-purple-400 shrink-0">•</span>
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 问题动机 */}
          {sr.problem_and_motivation && (
            <div>
              <div className="text-xs font-medium text-gray-400 mb-1">问题与动机</div>
              <p className="text-sm text-gray-600">{sr.problem_and_motivation}</p>
            </div>
          )}

          {/* 方法概述 */}
          {sr.method_overview && (
            <div>
              <div className="text-xs font-medium text-gray-400 mb-1">方法概述</div>
              <p className="text-sm text-gray-600">{sr.method_overview}</p>
              {sr.method_steps && sr.method_steps.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {sr.method_steps.map((s, i) => (
                    <span key={i} className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">
                      <span className="w-4 h-4 rounded-full bg-purple-400 text-white text-[10px] flex items-center justify-center">
                        {i + 1}
                      </span>
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 核心图表 */}
          {sr.core_figures && sr.core_figures.length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-400 mb-2">核心图表</div>
              <div className="space-y-2">
                {sr.core_figures.map((fig, i) => (
                  <div key={i} className="bg-gray-50 rounded p-2">
                    <div className="text-xs font-medium text-gray-700 mb-1">
                      Fig {fig.page_number + 1}: {fig.caption}
                    </div>
                    <div className="grid grid-cols-3 gap-1 text-[11px]">
                      <div>
                        <span className="text-gray-400">看什么：</span>
                        <span className="text-gray-600">{fig.what_to_look}</span>
                      </div>
                      <div>
                        <span className="text-gray-400">说明：</span>
                        <span className="text-gray-600">{fig.what_it_tells}</span>
                      </div>
                      <div>
                        <span className="text-gray-400">重要：</span>
                        <span className="text-gray-600">{fig.why_important}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 实验解读 */}
          {sr.experiment_read && (
            <div>
              <div className="text-xs font-medium text-gray-400 mb-1">实验解读</div>
              <p className="text-sm text-gray-600">{sr.experiment_read}</p>
            </div>
          )}

          {/* 贡献 / 局限 */}
          <div className="grid grid-cols-2 gap-3">
            {sr.contributions && sr.contributions.length > 0 && (
              <div className="bg-green-50 rounded p-2">
                <div className="text-xs font-medium text-green-500 mb-1">贡献</div>
                <ul className="space-y-0.5">
                  {sr.contributions.map((c, i) => (
                    <li key={i} className="text-xs text-gray-600 flex gap-1">
                      <span className="text-green-400">+</span>{c}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {sr.limitations && sr.limitations.length > 0 && (
              <div className="bg-orange-50 rounded p-2">
                <div className="text-xs font-medium text-orange-500 mb-1">局限性</div>
                <ul className="space-y-0.5">
                  {sr.limitations.map((l, i) => (
                    <li key={i} className="text-xs text-gray-600 flex gap-1">
                      <span className="text-orange-400">-</span>{l}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* 模型信息 */}
          {sr.model_used && (
            <div className="text-[10px] text-gray-300 text-right">
              由 {sr.model_used} 生成 · {sr.tokens_used} tokens
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function getAISettings(): { endpoint: string; apiKey: string; model: string } {
  try {
    const raw = localStorage.getItem('thesis-reader-settings')
    if (raw) {
      const s = JSON.parse(raw)
      return s.aiSettings || { endpoint: '', apiKey: '', model: 'gpt-4o' }
    }
  } catch { /* ignore */ }
  return { endpoint: '', apiKey: '', model: 'gpt-4o' }
}
