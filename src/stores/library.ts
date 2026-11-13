import { create } from 'zustand'

export interface LibraryStatus {
  running: boolean
  syncing: boolean
  directory: string
  last_scan: string | null
  revision: number
  paper_count: number
  errors: string[]
  scorer: { engine: 'cpp' | 'python'; available: boolean; reason: string }
}

export const useLibraryStore = create<{
  status: LibraryStatus | null
  error: string
  update: (status: LibraryStatus) => void
  fail: (error: string) => void
}>((set) => ({
  status: null,
  error: '',
  update: (status) => set({ status, error: '' }),
  fail: (error) => set({ error }),
}))
