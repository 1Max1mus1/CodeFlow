import { useState } from 'react'
import type { AIQuestion } from '../../types'

const CUSTOM_KEY = '__custom__'

interface AIConversationProps {
  questions: AIQuestion[]
  onAnswer: (questionId: string, answer: string) => Promise<void>
}

export function AIConversation({ questions, onAnswer }: AIConversationProps) {
  // Local form state: { [questionId]: answer }
  const [answers, setAnswers] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {}
    questions.forEach((q) => {
      if (q.userAnswer !== null) init[q.id] = q.userAnswer
    })
    return init
  })
  // Tracks which questions are in "custom input" mode
  const [customMode, setCustomMode] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const unanswered = questions.filter((q) => q.userAnswer === null)
  const allFilled = unanswered.every((q) => {
    const val = answers[q.id] ?? ''
    if (val === CUSTOM_KEY) return (customMode[q.id] ?? '').trim().length > 0
    return val.trim().length > 0
  })

  function getEffectiveAnswer(qId: string) {
    const val = answers[qId] ?? ''
    return val === CUSTOM_KEY ? (customMode[qId] ?? '').trim() : val.trim()
  }

  async function handleGenerate() {
    if (!allFilled || isSubmitting) return
    setIsSubmitting(true)
    try {
      for (const q of unanswered) {
        await onAnswer(q.id, getEffectiveAnswer(q.id))
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Question form */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        {questions.map((q, idx) => {
          const isAnswered = q.userAnswer !== null
          const currentVal = answers[q.id] ?? ''
          const isCustom = currentVal === CUSTOM_KEY

          return (
            <div key={q.id} className="space-y-2">
              {/* Question label */}
              <div className="flex items-start gap-2">
                <span className="shrink-0 text-xs font-bold text-blue-400 bg-blue-900/40 rounded px-1.5 py-0.5 mt-0.5">
                  Q{idx + 1}
                </span>
                <p className="text-sm text-gray-200 leading-snug">{q.question}</p>
              </div>

              {/* Answer area */}
              {isAnswered ? (
                /* Already submitted — read-only chip */
                <div className="ml-7 flex items-center gap-1.5">
                  <span className="text-xs text-green-400">✓</span>
                  <span className="text-xs text-gray-300 bg-gray-700 rounded px-2.5 py-1">
                    {q.userAnswer}
                  </span>
                </div>
              ) : q.options ? (
                /* Multiple-choice + custom option */
                <div className="ml-7 flex flex-col gap-1.5">
                  {q.options.map((opt) => (
                    <button
                      key={opt}
                      disabled={isSubmitting}
                      onClick={() => setAnswers((prev) => ({ ...prev, [q.id]: opt }))}
                      className={`text-left text-xs px-3 py-2 rounded border transition-all ${
                        currentVal === opt
                          ? 'bg-blue-800 border-blue-500 text-white'
                          : 'bg-gray-800 border-gray-600 text-gray-300 hover:border-blue-500 hover:text-white'
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      {currentVal === opt && <span className="mr-1.5 text-blue-300">●</span>}
                      {opt}
                    </button>
                  ))}

                  {/* Custom input option */}
                  <button
                    disabled={isSubmitting}
                    onClick={() => setAnswers((prev) => ({ ...prev, [q.id]: CUSTOM_KEY }))}
                    className={`text-left text-xs px-3 py-2 rounded border transition-all ${
                      isCustom
                        ? 'bg-purple-900/50 border-purple-500 text-white'
                        : 'bg-gray-800 border-gray-600 border-dashed text-gray-400 hover:border-purple-500 hover:text-white'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {isCustom && <span className="mr-1.5 text-purple-300">●</span>}
                    自定义输入…
                  </button>

                  {/* Inline text input when custom is selected */}
                  {isCustom && (
                    <input
                      autoFocus
                      type="text"
                      value={customMode[q.id] ?? ''}
                      disabled={isSubmitting}
                      onChange={(e) =>
                        setCustomMode((prev) => ({ ...prev, [q.id]: e.target.value }))
                      }
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && allFilled) {
                          e.preventDefault()
                          handleGenerate()
                        }
                      }}
                      placeholder="输入自定义内容…"
                      className="w-full bg-gray-900 border border-purple-600 rounded px-3 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-400 transition-colors disabled:opacity-50"
                    />
                  )}
                </div>
              ) : (
                /* Free-text textarea */
                <textarea
                  value={currentVal}
                  disabled={isSubmitting}
                  onChange={(e) =>
                    setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                  }
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey && allFilled) {
                      e.preventDefault()
                      handleGenerate()
                    }
                  }}
                  placeholder="Type your answer… (Enter to generate)"
                  rows={3}
                  className="ml-7 w-[calc(100%-1.75rem)] bg-gray-800 border border-gray-600 rounded px-3 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none transition-colors disabled:opacity-50"
                />
              )}
            </div>
          )
        })}
      </div>

      {/* Generate button */}
      <div className="shrink-0 px-4 pb-4 pt-2 border-t border-gray-700">
        <button
          onClick={handleGenerate}
          disabled={!allFilled || isSubmitting}
          className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold py-2.5 rounded transition-colors"
        >
          {isSubmitting ? 'Generating…' : 'Generate →'}
        </button>
        {!allFilled && !isSubmitting && (
          <p className="text-xs text-gray-600 text-center mt-1.5">
            Fill in all fields above to continue
          </p>
        )}
      </div>
    </div>
  )
}
