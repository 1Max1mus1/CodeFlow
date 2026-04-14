import { useState, useEffect } from 'react'
import type { EntryPoint, ParsedProject } from '../../types'

const BASE_URL_KEY = 'codeflow_test_base_url'

interface RouteTestPanelProps {
  entryPoint: EntryPoint | null
  project: ParsedProject | null
}

type FieldValue = string | number | boolean | null

// Derive a sensible default value from a type string
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

export function RouteTestPanel({ entryPoint, project }: RouteTestPanelProps) {
  const [baseUrl, setBaseUrl] = useState<string>(
    () => localStorage.getItem(BASE_URL_KEY) ?? 'http://localhost:8000'
  )
  const [fieldValues, setFieldValues] = useState<Record<string, FieldValue>>({})
  const [pathParams, setPathParams] = useState<Record<string, string>>({})
  const [isSending, setIsSending] = useState(false)
  const [response, setResponse] = useState<{
    status: number
    body: unknown
    ms: number
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Parse method + path from entryPoint.label ("POST /tasks/{task_id}")
  const [method, routePath] = entryPoint?.label.split(' ') ?? ['GET', '/']

  // Extract {param} placeholders from path
  const pathParamNames = [...(routePath?.matchAll(/\{(\w+)\}/g) ?? [])].map((m) => m[1])

  // Resolve the request body schema from the function's usesSchemas
  const fn = project?.functions.find((f) => f.id === entryPoint?.functionId) ?? null
  const bodySchema =
    fn?.usesSchemas
      .map((sid) => project?.schemas.find((s) => s.id === sid))
      .find(Boolean) ?? null

  // Reset state when entry point changes
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
        setError(data.detail ?? `Proxy error ${res.status}`)
      } else {
        setResponse({ status: data.statusCode ?? data.status_code, body: data.body, ms: Math.round(performance.now() - t0) })
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

  return (
    <div className="flex flex-col flex-1 overflow-hidden text-xs">
      {/* Base URL */}
      <div className="px-4 pt-3 pb-2 border-b border-gray-700 shrink-0 space-y-1">
        <label className="text-gray-500 uppercase text-[10px] font-bold tracking-wider">Base URL</label>
        <input
          type="text"
          value={baseUrl}
          onChange={(e) => handleBaseUrlChange(e.target.value)}
          className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500"
          placeholder="http://localhost:8000"
        />
      </div>

      {/* Route info */}
      <div className="px-4 py-2 border-b border-gray-700 shrink-0 flex items-center gap-2">
        <span className={`font-bold text-[11px] px-1.5 py-0.5 rounded ${
          method === 'GET'    ? 'bg-green-900 text-green-300' :
          method === 'POST'   ? 'bg-blue-900 text-blue-300' :
          method === 'PUT'    ? 'bg-yellow-900 text-yellow-300' :
          method === 'PATCH'  ? 'bg-orange-900 text-orange-300' :
          method === 'DELETE' ? 'bg-red-900 text-red-300' :
          'bg-gray-700 text-gray-300'
        }`}>{method}</span>
        <span className="font-mono text-gray-300 truncate">{routePath}</span>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {/* Path params */}
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

        {/* Request body */}
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

        {/* No body needed */}
        {!hasBody && pathParamNames.length === 0 && (
          <div className="text-gray-600 text-xs">No parameters needed for this route.</div>
        )}
      </div>

      {/* Send button */}
      <div className="shrink-0 px-4 pb-4 pt-2 border-t border-gray-700 space-y-3">
        <button
          onClick={handleSend}
          disabled={isSending}
          className="w-full bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold py-2.5 rounded transition-colors"
        >
          {isSending ? 'Sending…' : `▷ Send ${method}`}
        </button>

        {/* Error */}
        {error && (
          <div className="bg-red-950 border border-red-700 rounded p-2 text-red-300 break-all">
            {error}
          </div>
        )}

        {/* Response */}
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
