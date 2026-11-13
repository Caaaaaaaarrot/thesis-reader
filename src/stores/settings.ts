import { create } from 'zustand'

interface AISettings {
  endpoint: string
  apiKey: string
  model: string
}

interface SettingsState {
  theme: string
  autoLaunch: boolean
  aiSettings: AISettings
  setTheme: (theme: string) => void
  setAutoLaunch: (enabled: boolean) => void
  setAISettings: (settings: Partial<AISettings>) => void
}

const STORAGE_KEY = 'thesis-reader-settings'

function loadSettings(): { theme: string; autoLaunch: boolean; aiSettings: AISettings } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return {
    theme: 'light',
    autoLaunch: false,
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
    autoLaunch: state.autoLaunch,
    aiSettings: state.aiSettings,
  }))
}

const initial = loadSettings()

export const useSettingsStore = create<SettingsState>((set) => ({
  theme: initial.theme,
  autoLaunch: initial.autoLaunch ?? false,
  aiSettings: initial.aiSettings,

  setTheme: (theme: string) => {
    set({ theme })
    saveSettings({ theme, autoLaunch: useSettingsStore.getState().autoLaunch, aiSettings: useSettingsStore.getState().aiSettings })
  },

  setAutoLaunch: (autoLaunch: boolean) => {
    set({ autoLaunch })
    // 同步到 Electron
    if (window.electronAPI?.setAutoLaunch) {
      window.electronAPI.setAutoLaunch(autoLaunch)
    }
    saveSettings({ theme: useSettingsStore.getState().theme, autoLaunch, aiSettings: useSettingsStore.getState().aiSettings })
  },

  setAISettings: (aiSettings: Partial<AISettings>) => {
    set((s) => ({
      aiSettings: { ...s.aiSettings, ...aiSettings },
    }))
    saveSettings({
      theme: useSettingsStore.getState().theme,
      autoLaunch: useSettingsStore.getState().autoLaunch,
      aiSettings: useSettingsStore.getState().aiSettings,
    })
  },
}))
