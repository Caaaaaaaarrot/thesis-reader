import { useEffect, useMemo, useRef, useState } from 'react'
import { usePapersStore } from '../../stores/papers'
import {
  buildPaperGraph, GRAPH_COLORS, GRAPH_LABELS, GraphNode,
  GroupKind, initialPositions, Point,
} from '../../lib/paperGraph'

type View = { x: number; y: number; scale: number }
type Gesture = { id?: string; start: Point; origin: Point; moved: boolean }

function fittedView(points: Record<string, Point>, width: number, height: number): View {
  const values = Object.values(points)
  if (!values.length) return { x: 0, y: 0, scale: 1 }
  const xs = values.map((p) => p.x), ys = values.map((p) => p.y)
  const left = Math.min(...xs), right = Math.max(...xs), top = Math.min(...ys), bottom = Math.max(...ys)
  const scale = Math.min(1.6, Math.max(0.1, Math.min((width - 100) / (right - left + 100), (height - 100) / (bottom - top + 100))))
  return { scale, x: width / 2 - (left + right) / 2 * scale, y: height / 2 - (top + bottom) / 2 * scale }
}

export default function KnowledgeGraph() {
  const papers = usePapersStore((s) => s.papers)
  const selectedId = usePapersStore((s) => s.selectedId)
  const selectPaper = usePapersStore((s) => s.selectPaper)
  const [groups, setGroups] = useState<GroupKind[]>(['tag', 'venue', 'year'])
  const [labels, setLabels] = useState(false)
  const [focus, setFocus] = useState<string | null>(null)
  const [hover, setHover] = useState<string | null>(null)
  const [view, setView] = useState<View>({ x: 0, y: 0, scale: 1 })
  const [viewport, setViewport] = useState({ width: 1000, height: 700 })
  const viewportRef = useRef(viewport)
  const interacted = useRef(false)
  const graph = useMemo(() => buildPaperGraph(papers, groups), [papers, groups])
  const [positions, setPositions] = useState<Record<string, Point>>({})
  const current = useRef<Record<string, Point>>({})
  const gesture = useRef<Gesture | null>(null)
  const svg = useRef<SVGSVGElement>(null)
  const focusId = focus && graph.nodes.some((n) => n.id === focus) ? focus : selectedId ? `paper:${selectedId}` : null
  const active = graph.nodes.find((n) => n.id === (hover || focusId))

  const neighbors = useMemo(() => {
    const ids = new Set<string>()
    if (focusId) {
      ids.add(focusId)
      graph.edges.forEach((edge) => {
        if (edge.source === focusId) ids.add(edge.target)
        if (edge.target === focusId) ids.add(edge.source)
      })
    }
    return ids
  }, [graph, focusId])

  // 轻量力导向布局；有界迭代，静止后不占用持续动画资源。
  useEffect(() => {
    const seeded = initialPositions(graph.nodes)
    interacted.current = false
    current.current = Object.fromEntries(graph.nodes.map((n) => [n.id, current.current[n.id] || seeded[n.id]]))
    setPositions({ ...current.current })
    let frame = 0
    let step = 0
    const indices = new Map(graph.nodes.map((n, i) => [n.id, i]))
    const links = graph.edges.map((e) => [indices.get(e.source)!, indices.get(e.target)!])
    const tick = () => {
      const points = graph.nodes.map((n) => current.current[n.id])
      const forces = points.map(() => ({ x: 0, y: 0 }))
      const alpha = Math.max(0.04, 1 - step / 160)
      for (let i = 0; i < points.length; i++) {
        for (let j = i + 1; j < points.length; j++) {
          let dx = points[i].x - points[j].x
          let dy = points[i].y - points[j].y
          if (dx === 0 && dy === 0) { dx = 0.1; dy = 0.1 }
          const distance2 = Math.max(dx * dx + dy * dy, 60)
          const distance = Math.sqrt(distance2)
          const force = Math.min(1600 / distance2, 8) * alpha
          const fx = dx / distance * force
          const fy = dy / distance * force
          forces[i].x += fx; forces[i].y += fy
          forces[j].x -= fx; forces[j].y -= fy
        }
      }
      links.forEach(([a, b]) => {
        const dx = points[b].x - points[a].x
        const dy = points[b].y - points[a].y
        const distance = Math.max(1, Math.hypot(dx, dy))
        const force = (distance - 100) * 0.025 * alpha
        const fx = dx / distance * force
        const fy = dy / distance * force
        forces[a].x += fx; forces[a].y += fy
        forces[b].x -= fx; forces[b].y -= fy
      })
      graph.nodes.forEach((node, i) => {
        if (gesture.current?.id === node.id) return
        const p = points[i]
        current.current[node.id] = {
          x: Math.max(45, Math.min(955, p.x + forces[i].x + (500 - p.x) * 0.003 * alpha)),
          y: Math.max(45, Math.min(655, p.y + forces[i].y + (350 - p.y) * 0.003 * alpha)),
        }
      })
      setPositions({ ...current.current })
      if (++step < 160) frame = requestAnimationFrame(tick)
      else if (!interacted.current) setView(fittedView(current.current, viewportRef.current.width, viewportRef.current.height))
    }
    if (graph.nodes.length) frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [graph])

  const point = (clientX: number, clientY: number): Point => {
    const matrix = svg.current?.getScreenCTM()
    return matrix ? new DOMPoint(clientX, clientY).matrixTransform(matrix.inverse()) : { x: clientX, y: clientY }
  }
  const zoom = (factor: number, center: Point = { x: viewportRef.current.width / 2, y: viewportRef.current.height / 2 }) => {
    interacted.current = true
    setView((previous) => {
      const scale = Math.max(0.35, Math.min(4, previous.scale * factor))
      const ratio = scale / previous.scale
      return { scale, x: center.x - (center.x - previous.x) * ratio, y: center.y - (center.y - previous.y) * ratio }
    })
  }
  useEffect(() => {
    const element = svg.current
    if (!element) return
    const wheel = (event: WheelEvent) => {
      event.preventDefault()
      zoom(Math.exp(-event.deltaY * 0.0015), point(event.clientX, event.clientY))
    }
    element.addEventListener('wheel', wheel, { passive: false })
    return () => element.removeEventListener('wheel', wheel)
  }, [papers.length > 0])

  useEffect(() => {
    const element = svg.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      if (width <= 0 || height <= 0) return
      viewportRef.current = { width, height }
      setViewport({ width, height })
      setView(fittedView(current.current, width, height))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [papers.length > 0])

  const choose = (node: GraphNode) => {
    setFocus((previous) => previous === node.id ? null : node.id)
    if (node.paperId) selectPaper(node.paperId)
  }

  return (
    <div className="h-full flex flex-col bg-slate-50">
      <div className="px-4 py-3 bg-white/90 border-b border-gray-100 flex flex-wrap items-center gap-3 shrink-0">
        <div className="mr-auto">
          <h2 className="text-sm font-semibold text-gray-700">知识图谱</h2>
          <p className="text-[11px] text-gray-400 mt-0.5">{graph.nodes.filter((n) => n.kind === 'paper').length} 篇论文 · {graph.edges.length} 条关联</p>
        </div>
        {(['tag', 'venue', 'year'] as GroupKind[]).map((kind) => (
          <label key={kind} className="text-xs text-gray-500 flex items-center gap-1 cursor-pointer">
            <input type="checkbox" checked={groups.includes(kind)} onChange={() => setGroups((previous) => previous.includes(kind) ? previous.filter((g) => g !== kind) : [...previous, kind])} />
            <span style={{ color: GRAPH_COLORS[kind] }}>{GRAPH_LABELS[kind]}</span>
          </label>
        ))}
        <label className="text-xs text-gray-500 flex items-center gap-1 cursor-pointer"><input type="checkbox" checked={labels} onChange={(e) => setLabels(e.target.checked)} />标题</label>
      </div>
      <div className="flex-1 min-h-0 relative overflow-hidden">
        {papers.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400 text-sm gap-2">
            <p>当前没有可展示的论文</p><p className="text-xs">导入 PDF，或调整上方搜索和侧栏筛选。</p>
          </div>
        ) : (
          <svg ref={svg} viewBox={`0 0 ${viewport.width} ${viewport.height}`} className="w-full h-full touch-none select-none" role="group" aria-label="论文知识图谱，可拖动节点与画布、滚轮缩放"
            onPointerDown={(event) => {
              if (event.button !== 0) return
              event.preventDefault()
              interacted.current = true
              const target = (event.target as Element).closest('[data-node]')
              const id = target?.getAttribute('data-node') || undefined
              gesture.current = { id, start: point(event.clientX, event.clientY), origin: id ? { ...current.current[id] } : { x: view.x, y: view.y }, moved: false }
              event.currentTarget.setPointerCapture(event.pointerId)
            }}
            onPointerMove={(event) => {
              const action = gesture.current
              if (!action) return
              const p = point(event.clientX, event.clientY)
              const dx = p.x - action.start.x, dy = p.y - action.start.y
              if (Math.hypot(dx, dy) > 3) action.moved = true
              if (action.id) {
                current.current[action.id] = { x: action.origin.x + dx / view.scale, y: action.origin.y + dy / view.scale }
                setPositions({ ...current.current })
              } else setView((previous) => ({ ...previous, x: action.origin.x + dx, y: action.origin.y + dy }))
            }}
            onPointerUp={(event) => {
              const action = gesture.current
              gesture.current = null
              if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
              if (!action?.moved) {
                const node = graph.nodes.find((n) => n.id === action?.id)
                if (node) choose(node)
                else setFocus(null)
              }
            }}
            onPointerCancel={() => { gesture.current = null }}>
            <defs><pattern id="graph-dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="0.7" fill="#cbd5e1" /></pattern></defs>
            <rect width={viewport.width} height={viewport.height} fill="url(#graph-dots)" />
            <g transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}>
              {graph.edges.map((edge) => {
                const a = positions[edge.source], b = positions[edge.target]
                if (!a || !b) return null
                const highlighted = edge.source === focusId || edge.target === focusId
                return <line key={`${edge.source}|${edge.target}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={highlighted ? '#94a3b8' : '#cbd5e1'} strokeWidth={highlighted ? 2 : 1} opacity={focusId && !highlighted ? 0.12 : 0.7} />
              })}
              {graph.nodes.map((node) => {
                const p = positions[node.id]
                if (!p) return null
                const emphasized = node.id === focusId || node.id === hover
                const radius = node.kind === 'paper' ? 7 : 11 + Math.min(8, Math.sqrt(node.degree))
                return (
                  <g key={node.id} data-node={node.id} transform={`translate(${p.x} ${p.y})`} className="cursor-pointer outline-none"
                    opacity={focusId && !neighbors.has(node.id) && node.id !== hover ? 0.2 : 1}
                    tabIndex={0} role="button" aria-label={`${GRAPH_LABELS[node.kind]}：${node.label}`}
                    onFocus={() => setHover(node.id)} onBlur={() => setHover(null)}
                    onMouseEnter={() => setHover(node.id)} onMouseLeave={() => setHover(null)}
                    onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(node) } }}>
                    <title>{`${GRAPH_LABELS[node.kind]}：${node.label}\n${node.degree} 条关联`}</title>
                    {emphasized && <circle r={radius + 5} fill={GRAPH_COLORS[node.kind]} opacity={0.15} />}
                    <circle r={radius} fill={GRAPH_COLORS[node.kind]} stroke="white" strokeWidth={2} />
                    {node.kind !== 'paper' && <text textAnchor="middle" dy="4" fill="white" fontSize="10" pointerEvents="none">{node.degree}</text>}
                    {(node.kind !== 'paper' || labels || emphasized) && <text y={radius + 16} textAnchor="middle" fill="#475569" fontSize="11" paintOrder="stroke" stroke="#f8fafc" strokeWidth="3" pointerEvents="none">{node.label.length > 26 ? `${node.label.slice(0, 26)}…` : node.label}</text>}
                  </g>
                )
              })}
            </g>
          </svg>
        )}
        <div className="absolute right-3 top-3 flex gap-1 rounded-lg bg-white shadow-sm border border-gray-200 p-1">
          <button aria-label="放大图谱" className="w-8 h-7 text-gray-600 hover:bg-gray-50" onClick={() => zoom(1.25)}>＋</button>
          <button aria-label="缩小图谱" className="w-8 h-7 text-gray-600 hover:bg-gray-50" onClick={() => zoom(0.8)}>－</button>
          <button className="px-2 h-7 text-xs text-gray-500 hover:bg-gray-50" onClick={() => { setView(fittedView(current.current, viewport.width, viewport.height)); setFocus(null) }}>重置</button>
        </div>
        {active && <div className="absolute bottom-3 left-3 right-3 max-w-sm bg-white/95 border border-gray-200 rounded-lg px-3 py-2 shadow-sm pointer-events-none">
          <div className="text-[10px] font-medium" style={{ color: GRAPH_COLORS[active.kind] }}>{GRAPH_LABELS[active.kind]}</div>
          <p className="text-xs text-gray-700 mt-1 break-words">{active.label}</p>
          <p className="text-[10px] text-gray-400 mt-1">{active.kind === 'paper' ? `${active.degree} 条关联 · 点击查看论文详情` : `${active.degree} 篇关联论文 · 点击突出显示`}</p>
        </div>}
      </div>
      <div className="px-4 py-2 border-t border-gray-100 bg-white text-[10px] text-gray-400 flex flex-wrap items-center gap-x-4 gap-y-1 shrink-0">
        <span><span className="inline-block w-2 h-2 rounded-full bg-blue-500 mr-1" />论文</span>
        <span>拖动节点或空白画布 · 滚轮缩放 · 上方筛选同时作用于图谱</span>
        <span>连线表示共同属性</span>
        {graph.omitted > 0 && <span className="text-amber-600">当前展示前 200 篇，另有 {graph.omitted} 篇；可筛选缩小范围。</span>}
      </div>
    </div>
  )
}
