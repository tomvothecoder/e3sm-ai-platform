import { FormEvent, useState } from 'react'
import { citationLabel, citationUrl, queryAssistant, type QueryResponse } from './api'
import './styles.css'

const starters = [
  'How do I choose an E3SM compset?',
  'How do I build and submit an E3SM case?',
  'How do I configure EAMxx diagnostics?',
]

const exampleGroups = [
  {
    title: 'Getting started',
    questions: [
      'How do I choose an E3SM compset?',
      'How do I create an E3SM case?',
      'Where are grid aliases and resolutions documented?',
    ],
  },
  {
    title: 'Running E3SM',
    questions: [
      'How do I build and submit an E3SM case?',
      'What does case.setup do?',
      'What does case.submit do?',
    ],
  },
  {
    title: 'Components',
    questions: [
      'How does E3SM represent the land carbon cycle?',
      'What role does MPAS play in E3SM?',
      'Where can I find ELM documentation?',
    ],
  },
  {
    title: 'Diagnostics',
    questions: [
      'How do I configure EAMxx YAML diagnostics output?',
      'How do I use E3SM Diagnostics?',
      'How do EAMxx diagnostics work?',
    ],
  },
]

function generationModeLabel(mode: QueryResponse['generation_mode']) {
  if (mode === 'llm') return 'LLM response'
  if (mode === 'deterministic_fallback') return 'Deterministic fallback'
  return 'Deterministic response'
}

function EvidencePanel({ response }: { response: QueryResponse }) {
  const evidence = response.evidence
  const [scoreHelpOpen, setScoreHelpOpen] = useState(false)

  return (
    <section className="evidence-section">
      <button
        aria-expanded={scoreHelpOpen}
        aria-label="What do evidence scores mean?"
        className="evidence-help-toggle"
        onClick={() => setScoreHelpOpen((isOpen) => !isOpen)}
        type="button"
      >
        ?
      </button>
      {scoreHelpOpen && (
        <div className="evidence-score-help" role="note">
          <strong>How evidence is ranked</strong>
          <p>
            Retrieved passages come from the curated E3SM corpus. Lexical retrieval is the
            default; semantic and hybrid retrieval can be enabled when configured.
          </p>
          <p>
            <b>Retrieval score</b> is a relative relevance value used to rank passages. It is
            not a confidence percentage.
          </p>
          <p>
            <b>Lexical coverage</b> is the percentage of normalized query terms found in a
            passage and its source metadata.
          </p>
        </div>
      )}
      <details className="evidence-panel">
        <summary>
          <span>Evidence</span>
          <span className="count">{evidence.length} retrieved</span>
        </summary>
        <div className="evidence-list">
          {evidence.length ? (
            evidence.map((item, index) => (
              <article
                className="evidence-item"
                key={`${item.title ?? item.sourceLabel ?? 'evidence'}-${index}`}
              >
                <div className="evidence-meta">
                  {item.sourceLabel ?? `Retrieved passage ${index + 1}`}
                  {typeof item.score === 'number'
                    ? ` · retrieval score ${item.score.toFixed(3)}`
                    : ''}
                  {typeof item.coverage === 'number'
                    ? ` · ${(item.coverage * 100).toFixed(0)}% lexical coverage`
                    : ''}
                </div>
                <strong>{item.title}</strong>
                <p>{item.content ?? 'No passage text was provided.'}</p>
              </article>
            ))
          ) : (
            <p className="empty-copy">No retrieved passages were returned for this answer.</p>
          )}
        </div>
      </details>
    </section>
  )
}

function DebugPanel({ response }: { response: QueryResponse }) {
  return (
    <details className="debug-panel">
      <summary>
        Debug details <span>⌄</span>
      </summary>
      <div className="debug-grid">
        <div>
          <span>Selected route</span>
          <code>{response.route ?? 'Not provided'}</code>
        </div>
        <div>
          <span>Retrieved sources</span>
          <code>{response.evidence.length}</code>
        </div>
        <div>
          <span>Evidence status</span>
          <code>{response.insufficient_evidence ? 'Insufficient' : 'Available'}</code>
        </div>
      </div>
    </details>
  )
}

export default function App() {
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<QueryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [examplesOpen, setExamplesOpen] = useState(false)

  function selectExample(example: string) {
    setQuestion(example)
    setExamplesOpen(false)
    void askQuestion(example)
  }

  async function askQuestion(value: string) {
    const trimmed = value.trim()
    if (!trimmed || loading) return
    setLoading(true)
    setError('')
    setResponse(null)
    try {
      setResponse(await queryAssistant(trimmed))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong while reaching the assistant.')
    } finally {
      setLoading(false)
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void askQuestion(question)
  }

  return (
    <main className="shell">
      <header className="masthead">
        <a className="wordmark" href="https://e3sm.org/" aria-label="E3SM home">
          <img src="https://e3sm.org/wp-content/themes/e3sm/assets/images/e3sm-logo-decade.png" alt="E3SM" />
        </a>
        <nav aria-label="E3SM resources">
          <a href="https://e3sm.org/about/">About</a>
          <a href="https://e3sm.org/resources/model/">Model</a>
          <a href="https://e3sm.org/resources/data/">Data</a>
          <a href="https://e3sm.org/tools/">Tools</a>
        </nav>
        <div className="utility-links">
          <a href="https://docs.e3sm.org/">E3SM Docs</a>
          <span>AI Assistant</span>
        </div>
      </header>

      <section className={`stage ${response ? 'has-response' : ''}`} aria-live="polite">
        {!response && !loading && !error && (
          <div className="welcome">
            <p className="eyebrow">Energy Exascale Earth System Model</p>
            <h1>
              E3SM knowledge
              <br />
              <em>assistant</em>
            </h1>
            <p className="intro">
              Ask questions about the model, its data, and Earth system science. Answers are grounded in E3SM documentation and research material.
            </p>
          </div>
        )}

        {loading && (
          <div className="thinking">
            <span className="orb" />
            <p>
              Tracing the evidence<span className="ellipsis">...</span>
            </p>
          </div>
        )}
        {error && (
          <div className="error" role="alert">
            <strong>Unable to get an answer.</strong>
            <p>{error}</p>
          </div>
        )}

        {response && (
          <article className="answer-card">
            <div className="answer-topline">
              <span className="eyebrow">E3SM-ASSIST</span>
              <div className="answer-statuses">
                <span className={`generation-mode ${response.generation_mode ?? 'deterministic'}`}>
                  {generationModeLabel(response.generation_mode)}
                </span>
                {response.insufficient_evidence && <span className="caution">Limited evidence</span>}
              </div>
            </div>
            <div className="answer-text">{response.answer}</div>
            {response.citations.length > 0 && (
              <section className="citations">
                <p>Sources</p>
                <div>
                  {response.citations.map((citation, index) => {
                    const url = citationUrl(citation)
                    const label = citationLabel(citation, index)

                    return url ? (
                      <a
                        key={`${url}-${index}`}
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {label} <span>↗</span>
                      </a>
                    ) : (
                      <span key={`${label}-${index}`}>{label}</span>
                    )
                  })}
                </div>
              </section>
            )}
            <EvidencePanel response={response} />
            <DebugPanel response={response} />
          </article>
        )}
      </section>

      <section className="query-area">
        <form onSubmit={submit}>
          <label className="sr-only" htmlFor="question">
            Ask E3SM-ASSIST a question
          </label>
          <textarea
            id="question"
            rows={2}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                event.currentTarget.form?.requestSubmit()
              }
            }}
            placeholder="Ask a question about E3SM..."
          />
          <button
            type="submit"
            disabled={!question.trim() || loading}
            aria-label="Send question"
          >
            {loading ? '· · ·' : '↑'}
          </button>
        </form>
        <div className="starters" aria-label="Example questions">
          {starters.map((starter) => (
            <button key={starter} type="button" onClick={() => selectExample(starter)}>
              {starter}
            </button>
          ))}
        </div>
        <button className="explore-examples" type="button" onClick={() => setExamplesOpen(true)}>
          Explore example questions
        </button>
      </section>
      {examplesOpen && (
        <div
          className="example-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setExamplesOpen(false)
          }}
        >
          <section
            aria-labelledby="example-dialog-title"
            aria-modal="true"
            className="example-dialog"
            onKeyDown={(event) => {
              if (event.key === 'Escape') setExamplesOpen(false)
            }}
            role="dialog"
          >
            <div className="example-dialog-header">
              <div>
                <p className="eyebrow">Explore the corpus</p>
                <h2 id="example-dialog-title">Example questions</h2>
              </div>
              <button
                aria-label="Close example questions"
                autoFocus
                className="dialog-close"
                onClick={() => setExamplesOpen(false)}
                type="button"
              >
                ×
              </button>
            </div>
            <p className="example-dialog-intro">Choose a question to add it to the assistant.</p>
            <div className="example-groups">
              {exampleGroups.map((group) => (
                <section key={group.title} className="example-group" aria-labelledby={`${group.title}-examples`}>
                  <h3 id={`${group.title}-examples`}>{group.title}</h3>
                  {group.questions.map((example) => (
                    <button key={example} type="button" onClick={() => selectExample(example)}>
                      {example}
                    </button>
                  ))}
                </section>
              ))}
            </div>
          </section>
        </div>
      )}
      <footer>Answers are grounded in retrieved material. Verify details in the linked sources. <a href="https://e3sm.org/">Visit e3sm.org</a></footer>
    </main>
  )
}
