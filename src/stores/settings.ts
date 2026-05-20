import { create } from 'zustand'

interface AISettings {
  endpoint: string
  apiKey: string
  model: string
}

interface SettingsState {
  theme: string
  aiSettings: AISettings
  setTheme: (theme: string) => void
  setAISettings: (settings: Partial<AISettings>) => void
}

const STORAGE_KEY = 'thesis-reader-settings'

function loadSettings(): { theme: string; aiSettings: AISettings } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return {
    theme: 'light',
    aiSettings: {
      endpoint: 'https://api.openai.com/v1',
      apiKey: '',
      model: 'gpt-4o',
    },
  }
}

function saveSettings(state: Partial<SettingsState>): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    theme: state.theme,
    aiSettings: state.aiSettings,
  }))
}

const initial = loadSettings()

export const useSettingsStore = create<SettingsState>((set) => ({
  theme: initial.theme,
  aiSettings: initial.aiSettings,

  setTheme: (theme: string) => {
    set({ theme })
    saveSettings({ theme, aiSettings: useSettingsStore.getState().aiSettings })
  },

  setAISettings: (aiSettings: Partial<AISettings>) => {
    set((s) => ({
      aiSettings: { ...s.aiSettings, ...aiSettings },
    }))
    saveSettings({
      theme: useSettingsStore.getState().theme,
      aiSettings: useSettingsStore.getState().aiSettings,
    })
  },
}))
