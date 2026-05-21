import { useState, useRef, useCallback } from 'react'
import { getBaseUrl } from '../api/client'

interface SSEMessage {
  event: string
  data: Record<string, unknown>
}

export function useSSE() {
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(false)
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const connect = useCallback(async (
    url: string,
    body: object,
    onMessage: (msg: SSEMessage) => void,
    onComplete: () => void,
    onError: (err: string) => void,
  ) => {
    setLoading(true)
    setConnected(true)
    abortRef.current = new AbortController()

    try {
      const res = await fetch(`${getBaseUrl()}${url}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: abortRef.current.signal,
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: res.statusText }))
        onError(typeof errData === 'object' ? (errData as Record<string,unknown>).detail as string || res.statusText : res.statusText)
        return
      }

      const reader = res.body?.getReader()
      if (!reader) {
        onError('无法读取响应流')
        return
      }
      readerRef.current = reader

      const decoder = new TextDecoder()
      let buffer = ''
      let reading = true

      while (reading) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (currentEvent === 'error') {
                onError(data.message || '未知错误')
                reading = false
                break
              }
              if (currentEvent === 'done') {
                onMessage({ event: 'done', data })
                onComplete()
                reading = false
                break
              }
              onMessage({ event: currentEvent, data })
            } catch {
              // skip malformed lines
            }
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      onError(err instanceof Error ? err.message : '连接失败')
    } finally {
      setLoading(false)
      setConnected(false)
    }
  }, [])

  const abort = useCallback(() => {
    abortRef.current?.abort()
    readerRef.current?.cancel()
    setLoading(false)
    setConnected(false)
  }, [])

  return { connected, loading, connect, abort }
}
