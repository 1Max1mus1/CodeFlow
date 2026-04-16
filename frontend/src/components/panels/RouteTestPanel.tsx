import { useState, useEffect, useRef } from 'react'
import type { EntryPoint, ParsedProject } from '../../types'

const BASE_URL_KEY = 'codeflow_test_base_url'
const PORT_PRESETS = [3000, 5000, 8000, 8080]

type HealthStatus = 'idle' | 'checking' | 'ok' | 'error'
type FieldValue = string | number | boolean | null

interface RouteTestPanelProps {
  entryPoint: EntryPoint | null
  project: ParsedProject | null
}

function defaultForType(type: string | null): FieldValue {
  if (!type) return ''
  const t = type.toLowerCase().replace('optional[', '').replace(']', '').trim()
  if (t === 'int' || t === 'float') return 0
  if (t === 'bool') return false
  return ''
}

function statusColor(code: number) {
  if (code < 300) return 'text-green-400'
  if (code < 400) return 'text-yellow-400'
  return 'text-red-400'
}

const HEALTH_DOT: Record<HealthStatus, string> = {
  idle:     'bg-gray-600',
  checking: 'bg-yellow-500 animate-pulse',
  ok:       'bg-green-500',
  error:    'bg-red-500',
}

const HEALTH_TITLE: Record<HealthStatus, string> = {
  idle:     '未检测',
  checking: '检测中…',
  ok:       '服务可达',
  error:    '无法连接',
}

export function RouteTestPanel({ entryPoint, project }: RouteTestPanelProps) {
  const suggestedPort = project?.suggestedPort ?? null
  const suggestedUrl  = suggestedPort ? `http://localhost:${suggestedPort}` : null

  const [baseUrl, setBaseUrl] = useState<string>(() => {
    const cached = localStorage.getItem(BASE_URL_KEY)
    if (cached) return cached
    return suggestedUrl ?? 'http://localhost:8000'
  })
  const [fieldValues, setFieldValues]   = useState<Record<string, FieldValue>>({})
  const [pathParams,  setPathParams]    = useState<Record<string, string>>({})
  const [isSending,   setIsSending]     = useState(false)
  const [response,    setResponse]      = useState<{ status: number; body: unknown; ms: number } | null>(null)
  const [error,       setError]         = useState<string | null>(null)
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('idle')

  const healthTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Parse method + path from entryPoint.label ("POST /tasks/{task_id}")
  const [method, routePath] = entryPoint?.label.split(' ') ?? ['GET', '/']
  const pathParamNames = [...(routePath?.matchAll(/\{(\w+)\}/g) ?? [])].map((m) => m[1])

  const fn = project?.functions.find((f) => f.id === entryPoint?.functionId) ?? null
  const bodySchema =
    fn?.usesSchemas
      .map((sid) => project?.schemas.find((s) => s.id === sid))
      .find(Boolean) ?? null

  // Reset fields when entry point changes
  useEffect(() => {
    setResponse(null)
    setError(null)
    setFieldValues(
      Object.fromEntries(
        (bodySchema?.fields ?? []).map((f) => [f.name, f.default ?? defaultForType(f.type)])
      )
    )
    setPathParams(Object.fromEntries(pathParamNames.map((p) => [p, ''])))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entryPoint?.id])

  // Debounced health check on baseUrl change
  useEffect(() => {
    if (healthTimerRef.current) clearTimeout(healthTimerRef.current)
    setHealthStatus('checking')
    healthTimerRef.current = setTimeout(() => { void runHealthCheck(baseUrl) }, 600)
    return () => { if (healthTimerRef.current) clearTimeout(healthTimerRef.current) }
  }, [baseUrl])

  async function runHealthCheck(url: string) {
    try {
      const res = await fetch('/proxy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.replace(/\/$/, '') + '/', method: 'GET', headers: {}, body: null }),
      })
      // Any HTTP response (even 404) means the server process is reachable
      setHealthStatus(res.status < 600 ? 'ok' : 'error')
    } catch {
      setHealthStatus('error')
    }
  }

  function handleBaseUrlChange(v: string) {
    setBaseUrl(v)
    localStorage.setItem(BASE_URL_KEY, v)
  }

  function buildUrl() {
    let path = routePath ?? '/'
    for (const [k, v] of Object.entries(pathParams)) {
      path = path.replace(`{${k}}`, encodeURIComponent(v))
    }
    return baseUrl.replace(/\/$/, '') + path
  }

  function buildBody() {
    if (!bodySchema || ['GET', 'DELETE', 'HEAD'].includes(method)) return null
    const out: Record<string, FieldValue> = {}
    for (const f of bodySchema.fields) {
      const val = fieldValues[f.name]
      if (val !== '' && val !== null) out[f.name] = val
    }
    return out
  }

  async function handleSend() {
    setIsSending(true)
    setError(null)
    setResponse(null)
    const t0 = performance.now()
    try {
      const res = await fetch('/proxy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: buildUrl(),
          method,
          headers: { 'Content-Type': 'application/json' },
          body: buildBody(),
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        const rawDetail: string = data.detail ?? `Proxy error ${res.status}`
        const friendlyDetail = rawDetail.includes('Could not connect')
          ? `无法连接到 ${baseUrl}\n\n排查步骤：\n① 确认目标项目已启动（如 uvicorn main:app）\n② 确认 Base URL 端口与项目一致\n③ 确认防火墙未拦截本地请求`
          : rawDetail
        setError(friendlyDetail)
      } else {
        setResponse({
          status: data.statusCode ?? data.status_code,
          body: data.body,
          ms: Math.round(performance.now() - t0),
        })
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setIsSending(false)
    }
  }

  if (!entryPoint) {
    return (
      <div className="p-4 text-xs text-gray-500">
        Hover an entry point in the left sidebar and click ▷ to test it here.
      </div>
    )
  }

  const hasBody = bodySchema && !['GET', 'DELETE', 'HEAD'].includes(method)
  const showSuggestedBanner = suggestedUrl !== null && suggestedUrl !== baseUrl

  return (
    <div className="flex flex-col flex-1 overflow-hidden text-xs">

      {/* ── 目标服务地址 ── */}
      <div className="px-4 pt-3 pb-2 border-b border-gray-700 shrink-0 space-y-1.5">
        <label className="text-gray-500 uppercase text-[10px] font-bold tracking-wider flex items-center gap-1">
          目标服务地址
          <span
            title="这是你自己项目的运行地址（非 CodeFlow 自身），请在启动项目后填写正确端口"
            className="text-gray-600 cursor-help normal-case font-normal"
          >
            ⓘ
          </span>
        </label>

        {/* Input + health dot */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={baseUrl}
            onChange={(e) => handleBaseUrlChange(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="http://localhost:8000"
          />
          <span
            title={HEALTH_TITLE[healthStatus]}
            className={`w-2 h-2 rounded-full shrink-0 ${HEALTH_DOT[healthStatus]}`}
          />
        </div>

        {/* Quick port presets */}
        <div className="flex gap-1 flex-wrap">
          {PORT_PRESETS.map((port) => (
            <button
              key={port}
              onClick={() => handleBaseUrlChange(`http://localhost:${port}`)}
              className={`px-1.5 py-0.5 rounded text-[10px] border transition-colors ${
                baseUrl === `http://localhost:${port}`
                  ? 'border-blue-500 text-blue-300 bg-blue-950'
                  : 'border-gray-600 text-gray-500 hover:border-gray-400 hover:text-gray-300'
              }`}
            >
              :{port}
            </button>
          ))}
        </div>

        {/* Suggested port banner */}
        {showSuggestedBanner && (
          <div className="flex items-center justify-between bg-blue-950 border border-blue-700 rounded px-2 py-1.5">
            <span className="text-blue-300">
              检测到项目端口{' '}
              <span className="font-mono font-bold">{suggestedPort}</span>
            </span>
            <button
              onClick={() => handleBaseUrlChange(suggestedUrl!)}
              className="text-blue-400 hover:text-blue-200 underline ml-2 shrink-0"
            >
              使用此地址
            </button>
          </div>
        )}
      </div>

      {/* ── Route info ── */}
      <div className="px-4 py-2 border-b border-gray-700 shrink-0 flex items-center gap-2">
        <span className={`font-bold text-[11px] px-1.5 py-0.5 rounded ${
          method === 'GET'    ? 'bg-green-900 text-green-300' :
          method === 'POST'   ? 'bg-blue-900 text-blue-300'  :
          method === 'PUT'    ? 'bg-yellow-900 text-yellow-300' :
          method === 'PATCH'  ? 'bg-orange-900 text-orange-300' :
          method === 'DELETE' ? 'bg-red-900 text-red-300'    :
          'bg-gray-700 text-gray-300'
        }`}>{method}</span>
        <span className="font-mono text-gray-300 truncate">{routePath}</span>
      </div>

      {/* ── Params / body ── */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {pathParamNames.length > 0 && (
          <div className="space-y-2">
            <div className="text-gray-500 uppercase text-[10px] font-bold tracking-wider">Path Parameters</div>
            {pathParamNames.map((p) => (
              <div key={p} className="flex items-center gap-2">
                <span className="text-gray-400 font-mono w-24 shrink-0">{p}</span>
                <input
                  type="text"
                  value={pathParams[p] ?? ''}
                  onChange={(e) => setPathParams((prev) => ({ ...prev, [p]: e.target.value }))}
                  placeholder="value"
                  className="flex-1 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-blue-500"
                />
              </div>
            ))}
          </div>
        )}

        {hasBody && (
          <div className="space-y-2">
            <div className="text-gray-500 uppercase text-[10px] font-bold tracking-wider">
              Request Body
              <span className="ml-2 text-purple-400 normal-case font-normal">{bodySchema.name}</span>
            </div>
            {bodySchema.fields.map((f) => (
              <div key={f.name} className="flex items-center gap-2">
                <div className="w-28 shrink-0">
                  <span className="text-gray-300 font-mono">{f.name}</span>
                  {f.isOptional && <span className="text-gray-600 ml-1">?</span>}
                  <div className="text-gray-600 text-[10px] font-mono truncate">{f.type}</div>
                </div>
                {f.type?.toLowerCase().includes('bool') ? (
                  <select
                    value={String(fieldValues[f.name] ?? 'false')}
                    onChange={(e) =>
                      setFieldValues((prev) => ({ ...prev, [f.name]: e.target.value === 'true' }))
                    }
                    className="flex-1 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-blue-500"
                  >
                    <option value="true">true</option>
                    <option value="false">false</option>
                  </select>
                ) : (
                  <input
                    type={f.type?.toLowerCase().includes('int') || f.type?.toLowerCase().includes('float') ? 'number' : 'text'}
                    value={fieldValues[f.name] as string ?? ''}
                    onChange={(e) => {
                      const raw = e.target.value
                      const isNum = f.type?.toLowerCase().includes('int') || f.type?.toLowerCase().includes('float')
                      setFieldValues((prev) => ({
                        ...prev,
                        [f.name]: isNum && raw !== '' ? Number(raw) : raw,
                      }))
                    }}
                    placeholder={f.default ? String(f.default) : f.isOptional ? 'optional' : 'required'}
                    className="flex-1 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-blue-500 placeholder-gray-600"
                  />
                )}
              </div>
            ))}
          </div>
        )}

        {!hasBody && pathParamNames.length === 0 && (
          <div className="text-gray-600 text-xs">No parameters needed for this route.</div>
        )}
      </div>

      {/* ── Send + response ── */}
      <div className="shrink-0 px-4 pb-4 pt-2 border-t border-gray-700 space-y-3">

        {/* Connection warning */}
        {healthStatus === 'error' && (
          <div className="bg-yellow-950 border border-yellow-700 rounded px-2 py-1.5 space-y-0.5">
            <div className="font-semibold text-yellow-300">目标服务未响应</div>
            <div className="text-yellow-500">① 确认你的项目已启动（如 uvicorn main:app）</div>
            <div className="text-yellow-500">② 确认 Base URL 端口与项目一致</div>
            <div className="text-yellow-500">③ 确认防火墙未拦截本地请求</div>
          </div>
        )}

        <button
          onClick={handleSend}
          disabled={isSending}
          className="w-full bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold py-2.5 rounded transition-colors"
        >
          {isSending ? 'Sending…' : `▷ Send ${method}`}
        </button>

        {error && (
          <div className="bg-red-950 border border-red-700 rounded p-2 text-red-300 whitespace-pre-wrap break-all">
            {error}
          </div>
        )}

        {response && (
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className={`font-bold text-sm ${statusColor(response.status)}`}>
                {response.status}
              </span>
              <span className="text-gray-600">{response.ms} ms</span>
            </div>
            <pre className="bg-gray-950 rounded p-2 text-[11px] font-mono text-gray-300 overflow-auto max-h-48 leading-relaxed whitespace-pre-wrap break-all">
              {JSON.stringify(response.body, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
