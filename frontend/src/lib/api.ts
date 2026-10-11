import { useCallback, useEffect, useRef, useState } from 'react'

export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? ''

export class ApiError extends Error {
  status: number
  detail: unknown
  constructor(status: number, message: string, detail?: unknown) {
    super(message)
    this.status = status
    this.detail = detail
  }
}

function describe(status: number, body: any): string {
  if (body?.error === 'validation_error' && Array.isArray(body.detail)) {
    return body.detail.map((d: any) => (d.field ? `${d.field}: ${d.message}` : d.message)).join(' · ')
  }
  if (typeof body?.detail === 'string') return body.detail
  return `Request failed (${status})`
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the Imboni API. Check that the backend is running.')
  }
  if (res.status === 204) return undefined as T
  const body = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, describe(res.status, body), body?.detail)
  return body as T
}

const cache = new Map<string, unknown>()

/** GET with an in-memory cache; returns {data, error, loading, reload}. */
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(() => (path && cache.has(path) ? (cache.get(path) as T) : null))
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState<boolean>(!!path && !cache.has(path))
  const current = useRef(path)

  const load = useCallback(
    (force = false) => {
      if (!path) return
      current.current = path
      if (!force && cache.has(path)) {
        setData(cache.get(path) as T)
        setLoading(false)
        setError(null)
        return
      }
      setLoading(true)
      setError(null)
      apiFetch<T>(path)
        .then((d) => {
          cache.set(path, d)
          if (current.current === path) setData(d)
        })
        .catch((e: ApiError) => {
          if (current.current === path) setError(e)
        })
        .finally(() => {
          if (current.current === path) setLoading(false)
        })
    },
    [path],
  )

  useEffect(() => {
    load()
  }, [load])

  return { data, error, loading, reload: () => load(true) }
}

/** POST JSON and trigger a browser download of the response (CSV/PDF exports). */
export async function downloadPost(path: string, body: unknown, fallbackName: string) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const b = await res.json().catch(() => null)
    throw new ApiError(res.status, describe(res.status, b))
  }
  saveBlob(await res.blob(), filenameFrom(res) ?? fallbackName)
}

export function downloadUrl(path: string) {
  return `${API_BASE}${path}`
}

function filenameFrom(res: Response): string | null {
  const cd = res.headers.get('Content-Disposition') ?? ''
  const m = /filename="?([^";]+)"?/.exec(cd)
  return m ? m[1] : null
}

function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
