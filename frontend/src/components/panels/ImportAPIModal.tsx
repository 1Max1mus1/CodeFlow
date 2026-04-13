import { useState } from 'react'
import type { FieldInfo } from '../../types'

interface ImportAPIModalProps {
  onConfirm: (params: {
    name: string
    endpoint: string
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
    outputSchema: FieldInfo[]
    description: string | null
  }) => void
  onCancel: () => void
}

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] as const

export function ImportAPIModal({ onConfirm, onCancel }: ImportAPIModalProps) {
  const [name, setName] = useState('')
  const [endpoint, setEndpoint] = useState('')
  const [method, setMethod] = useState<typeof HTTP_METHODS[number]>('POST')
  const [description, setDescription] = useState('')
  // Output schema: list of {name, type} pairs
  const [outputFields, setOutputFields] = useState<Array<{ name: string; type: string }>>([
    { name: '', type: 'str' },
  ])

  function addField() {
    setOutputFields((prev) => [...prev, { name: '', type: 'str' }])
  }

  function removeField(idx: number) {
    setOutputFields((prev) => prev.filter((_, i) => i !== idx))
  }

  function setFieldName(idx: number, value: string) {
    setOutputFields((prev) => prev.map((f, i) => (i === idx ? { ...f, name: value } : f)))
  }

  function setFieldType(idx: number, value: string) {
    setOutputFields((prev) => prev.map((f, i) => (i === idx ? { ...f, type: value } : f)))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const validFields = outputFields.filter((f) => f.name.trim())
    onConfirm({
      name: name.trim(),
      endpoint: endpoint.trim(),
      method,
      outputSchema: validFields.map((f) => ({
        name: f.name.trim(),
        type: f.type.trim() || 'str',
        isOptional: false,
        default: null,
        description: null,
      })),
      description: description.trim() || null,
    })
  }

  const canSubmit = name.trim() !== '' && endpoint.trim() !== ''

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/50 z-20">
      <div className="bg-gray-800 border border-gray-600 rounded-lg p-6 w-[480px] shadow-2xl max-h-[80vh] overflow-y-auto">
        <h3 className="text-white font-semibold mb-4">Import External API</h3>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Name */}
          <div>
            <label className="text-xs text-gray-400 block mb-1">API Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="MinerU API"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Method + Endpoint */}
          <div className="flex gap-2">
            <div className="w-28">
              <label className="text-xs text-gray-400 block mb-1">Method</label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value as typeof method)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              >
                {HTTP_METHODS.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="text-xs text-gray-400 block mb-1">Endpoint URL</label>
              <input
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder="https://api.example.com/v1/parse"
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="text-xs text-gray-400 block mb-1">Description (optional)</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this API do?"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Output schema */}
          <div>
            <label className="text-xs text-gray-400 block mb-2">Output Schema Fields</label>
            <div className="flex flex-col gap-2">
              {outputFields.map((field, idx) => (
                <div key={idx} className="flex gap-2 items-center">
                  <input
                    value={field.name}
                    onChange={(e) => setFieldName(idx, e.target.value)}
                    placeholder="field_name"
                    className="flex-1 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200 font-mono focus:outline-none focus:border-blue-500"
                  />
                  <input
                    value={field.type}
                    onChange={(e) => setFieldType(idx, e.target.value)}
                    placeholder="str"
                    className="w-24 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200 font-mono focus:outline-none focus:border-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => removeField(idx)}
                    className="text-gray-500 hover:text-red-400 text-lg leading-none"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addField}
              className="mt-2 text-xs text-blue-400 hover:text-blue-300"
            >
              + Add field
            </button>
          </div>

          {/* Buttons */}
          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={!canSubmit}
              className="flex-1 bg-green-700 hover:bg-green-600 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium rounded px-4 py-2 transition-colors"
            >
              Import
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm font-medium rounded px-4 py-2 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
