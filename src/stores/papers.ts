import { create } from 'zustand'
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client'

export interface SpeedReadData {
  status: string
  one_sentence: string
  quick_takeaways: string[]
  problem_and_motivation: string
  method_overview: string
  method_steps: string[]
  core_figures: CoreFigure[]
  experiment_read: string
  contributions: string[]
  limitations: string[]
  deep_read_suggestions: string[]
  model_used: string
  tokens_used: number
  error_message: string
}

export interface CoreFigure {
  page_number: number
  caption: string
  what_to_look: string
  what_it_tells: string
  why_important: string
  image_base64?: string
}

export interface Paper {
  id: string
  file_path: string
  title: string
  authors: string
  year: number | null
  venue: string
  tags: string[]
  read: boolean
  note: string
  bibtex: string
  date_added: string
  page_count: number
  file_size: number
  speed_read: SpeedReadData | null
}

export interface VenueItem {
  name: string
  count: number
}

export interface TagItem {
  name: string
  count: number
}

interface FilterState {
  search: string
  venue: string
  tag: string
  read: string
  sort: string
  order: string
}

type GenPhase = 'idle' | 'extracting' | 'scoring' | 'rendering' | 'calling_llm'

interface GenState {
  phase: GenPhase
  fields: Record<string, string>
}

interface PapersState {
  view: 'list' | 'graph'
  setView: (view: 'list' | 'graph') => void
  papers: Paper[]
  venues: VenueItem[]
  tags: TagItem[]
  loading: boolean
  filter: FilterState
  selectedId: string | null
  generating: Record<string, GenState>

  fetchPapers: () => Promise<void>
  fetchVenues: () => Promise<void>
  fetchTags: () => Promise<void>
  importPaper: (filePath: string) => Promise<void>
  updatePaper: (id: string, data: Partial<Paper>) => Promise<void>
  deletePaper: (id: string) => Promise<void>
  setFilter: (filter: Partial<FilterState>) => void
  selectPaper: (id: string | null) => void
  updateSpeedRead: (paperId: string, data: SpeedReadData) => void
  reindexPaper: (paperId: string) => Promise<void>
  startGenerating: (paperId: string) => void
  updateGenerating: (paperId: string, update: Partial<GenState>) => void
  finishGenerating: (paperId: string) => void
}

export const usePapersStore = create<PapersState>((set, get) => ({
  view: 'list',
  setView: (view) => set({ view }),
  papers: [],
  venues: [],
  tags: [],
  loading: false,
  filter: {
    search: '',
    venue: '',
    tag: '',
    read: 'all',
    sort: 'date_added',
    order: 'desc',
  },
  selectedId: null,
  generating: {},

  fetchPapers: async () => {
    set({ loading: true })
    try {
      const { search, venue, tag, read, sort, order } = get().filter
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (venue) params.set('venue', venue)
      if (tag) params.set('tag', tag)
      if (read !== 'all') params.set('read', read)
      if (sort) params.set('sort', sort)
      if (order) params.set('order', order)

      const papers = await apiGet<Paper[]>(`/api/papers?${params.toString()}`)
      set({ papers, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchVenues: async () => {
    try {
      const venues = await apiGet<VenueItem[]>('/api/venues')
      set({ venues })
    } catch { /* ignore */ }
  },

  fetchTags: async () => {
    try {
      const tags = await apiGet<TagItem[]>('/api/tags')
      set({ tags })
    } catch { /* ignore */ }
  },

  importPaper: async (filePath: string) => {
    await apiPost<Paper>('/api/papers/import', { file_path: filePath })
    get().fetchPapers()
    get().fetchVenues()
    get().fetchTags()
    window.electronAPI?.updateTrayPapers()
  },

  updatePaper: async (id: string, data: Partial<Paper>) => {
    await apiPut<Paper>(`/api/papers/${id}`, data)
    get().fetchPapers()
  },

  deletePaper: async (id: string) => {
    await apiDelete(`/api/papers/${id}`)
    set({ selectedId: null })
    get().fetchPapers()
    get().fetchVenues()
    get().fetchTags()
    window.electronAPI?.updateTrayPapers()
  },

  setFilter: (filter: Partial<FilterState>) => {
    set((s) => ({ filter: { ...s.filter, ...filter } }))
    get().fetchPapers()
  },

  selectPaper: (id: string | null) => set({ selectedId: id }),

  updateSpeedRead: (paperId: string, data: SpeedReadData) => {
    set((s) => ({
      papers: s.papers.map((p) =>
        p.id === paperId ? { ...p, speed_read: data } : p
      ),
    }))
  },

  reindexPaper: async (paperId: string) => {
    await apiPost<Paper>(`/api/papers/${paperId}/reindex`)
    get().fetchPapers()
    get().fetchVenues()
  },

  startGenerating: (paperId: string) => {
    set((s) => ({
      generating: { ...s.generating, [paperId]: { phase: 'extracting', fields: {} } }
    }))
  },

  updateGenerating: (paperId: string, update: Partial<GenState>) => {
    set((s) => {
      const cur = s.generating[paperId] || { phase: 'idle', fields: {} }
      return { generating: { ...s.generating, [paperId]: { ...cur, ...update } } }
    })
  },

  finishGenerating: (paperId: string) => {
    set((s) => {
      const next = { ...s.generating }
      delete next[paperId]
      return { generating: next }
    })
  },
}))
