import type { ReactNode } from 'react'

interface MarkdownMessageProps {
  content: string
}

type Block =
  | { type: 'markdown'; text: string }
  | { type: 'code'; language: string; code: string }

export function MarkdownMessage({ content }: MarkdownMessageProps) {
  const blocks = splitCodeFences(content)

  return (
    <div className="space-y-2">
      {blocks.map((block, index) =>
        block.type === 'code' ? (
          <pre
            key={index}
            className="overflow-x-auto rounded bg-gray-950 border border-gray-700 px-3 py-2 text-[11px] leading-relaxed text-gray-100"
          >
            {block.language && (
              <div className="mb-1 text-[10px] uppercase tracking-wide text-gray-500">
                {block.language}
              </div>
            )}
            <code>{block.code}</code>
          </pre>
        ) : (
          <div key={index} className="space-y-1">
            {renderMarkdownLines(block.text)}
          </div>
        ),
      )}
    </div>
  )
}

function splitCodeFences(content: string): Block[] {
  const blocks: Block[] = []
  const fencePattern = /```([a-zA-Z0-9_-]+)?\n?([\s\S]*?)```/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = fencePattern.exec(content)) !== null) {
    if (match.index > lastIndex) {
      blocks.push({ type: 'markdown', text: content.slice(lastIndex, match.index) })
    }
    blocks.push({
      type: 'code',
      language: match[1] ?? '',
      code: match[2].replace(/\n$/, ''),
    })
    lastIndex = fencePattern.lastIndex
  }

  if (lastIndex < content.length) {
    blocks.push({ type: 'markdown', text: content.slice(lastIndex) })
  }

  return blocks.length > 0 ? blocks : [{ type: 'markdown', text: content }]
}

function renderMarkdownLines(text: string): ReactNode[] {
  return text.split('\n').map((line, index) => {
    const trimmed = line.trim()
    if (!trimmed) return <div key={index} className="h-1" />

    const heading = /^(#{1,3})\s+(.+)$/.exec(trimmed)
    if (heading) {
      const size = heading[1].length === 1 ? 'text-sm' : heading[1].length === 2 ? 'text-[13px]' : 'text-xs'
      return (
        <div key={index} className={`${size} font-semibold text-gray-100`}>
          {renderInline(heading[2])}
        </div>
      )
    }

    const bullet = /^[-*]\s+(.+)$/.exec(trimmed)
    if (bullet) {
      return (
        <div key={index} className="flex gap-2">
          <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-gray-500" />
          <span>{renderInline(bullet[1])}</span>
        </div>
      )
    }

    const numbered = /^\d+\.\s+(.+)$/.exec(trimmed)
    if (numbered) {
      return (
        <div key={index} className="flex gap-2">
          <span className="text-gray-500">{trimmed.split('.')[0]}.</span>
          <span>{renderInline(numbered[1])}</span>
        </div>
      )
    }

    if (trimmed.startsWith('> ')) {
      return (
        <blockquote key={index} className="border-l-2 border-gray-600 pl-2 text-gray-400">
          {renderInline(trimmed.slice(2))}
        </blockquote>
      )
    }

    return <p key={index}>{renderInline(trimmed)}</p>
  })
}

function renderInline(text: string): ReactNode[] {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={index} className="rounded bg-gray-950 px-1 py-0.5 font-mono text-[11px] text-blue-200">
          {part.slice(1, -1)}
        </code>
      )
    }
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={index} className="font-semibold text-gray-100">
          {part.slice(2, -2)}
        </strong>
      )
    }
    return part
  })
}
