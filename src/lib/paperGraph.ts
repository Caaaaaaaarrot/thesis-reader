import type { Paper } from '../stores/papers'

export type GroupKind = 'tag' | 'venue' | 'year'
export type NodeKind = 'paper' | GroupKind
export interface GraphNode {
  id: string
  label: string
  kind: NodeKind
  paperId?: string
  degree: number
}
export interface GraphEdge { source: string; target: string }
export interface PaperGraph { nodes: GraphNode[]; edges: GraphEdge[]; omitted: number }

export const GRAPH_COLORS: Record<NodeKind, string> = {
  paper: '#3b82f6', tag: '#8b5cf6', venue: '#10b981', year: '#f59e0b',
}
export const GRAPH_LABELS: Record<NodeKind, string> = {
  paper: '论文', tag: '标签', venue: '会议/期刊', year: '年份',
}

export function buildPaperGraph(papers: Paper[], groups: GroupKind[], limit = 200): PaperGraph {
  const nodes = new Map<string, GraphNode>()
  const edges: GraphEdge[] = []
  const visible = papers.slice(0, limit)
  const enabled = new Set(groups)
  for (const paper of visible) {
    const node: GraphNode = { id: `paper:${paper.id}`, label: paper.title || '(无标题)', kind: 'paper', paperId: paper.id, degree: 0 }
    nodes.set(node.id, node)
    const relations: [GroupKind, string][] = []
    if (enabled.has('tag')) for (const tag of paper.tags) relations.push(['tag', tag.trim()])
    if (enabled.has('venue')) relations.push(['venue', paper.venue.trim()])
    if (enabled.has('year') && paper.year != null) relations.push(['year', String(paper.year)])
    const seen = new Set<string>()
    for (const [kind, label] of relations) {
      if (!label) continue
      const id = `${kind}:${label}`
      if (seen.has(id)) continue
      seen.add(id)
      if (!nodes.has(id)) nodes.set(id, { id, label, kind, degree: 0 })
      nodes.get(id)!.degree++
      node.degree++
      edges.push({ source: node.id, target: id })
    }
  }
  return { nodes: [...nodes.values()], edges, omitted: Math.max(0, papers.length - visible.length) }
}

export interface Point { x: number; y: number }

export function initialPositions(nodes: GraphNode[]): Record<string, Point> {
  const positions: Record<string, Point> = {}
  nodes.forEach((node, i) => {
    const angle = i * 2.399963229728653
    const radius = 35 + Math.sqrt(i / Math.max(1, nodes.length)) * 260
    positions[node.id] = { x: 500 + Math.cos(angle) * radius, y: 350 + Math.sin(angle) * radius }
  })
  return positions
}
