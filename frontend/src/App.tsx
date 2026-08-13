import { FormEvent, useState } from 'react'
import { citationLabel, citationUrl, queryAssistant, type QueryResponse } from './api'
import './styles.css'

const starters = [
  'How does E3SM represent the land carbon cycle?',
  'What controls simulated Arctic sea ice extent?',
  'Explain the role of MPAS in E3SM.',
]

function EvidencePanel({ response }: { response: QueryResponse }) {
  const evidence = response.evidence
  return (
    <details className="evidence-panel">
      <summary><span>Evidence</span><span className="count">{evidence.length} retrieved</span></summary>
      <div className="evidence-list">
        {evidence.length ? evidence.map((item, index) => (
          <article className="evidence-item" key={`${item.title ?? item.sourceLabel ?? 'evidence'}-${index}`}>
            <div className="evidence-meta">{item.sourceLabel ?? `Retrieved passage ${index + 1}`}{typeof item.score === 'number' ? ` · ${(item.score * 100).toFixed(0)}% match` : ''}</div>
            <strong>{item.title}</strong>
            <p>{item.content ?? 'No passage text was provided.'}</p>
          </article>
        )) : <p className="empty-copy">No retrieved passages were returned for this answer.</p>}
      </div>
    </details>
  )
}

function DebugPanel({ response }: { response: QueryResponse }) {
  return (
    <details className="debug-panel">
      <summary>Debug details <span>⌄</span></summary>
      <div className="debug-grid">
        <div><span>Selected route</span><code>{response.route ?? 'Not provided'}</code></div>
        <div><span>Retrieved sources</span><code>{response.evidence.length}</code></div>
        <div><span>Evidence status</span><code>{response.insufficient_evidence ? 'Insufficient' : 'Available'}</code></div>
      </div>
    </details>
  )
}

export default function App() {
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<QueryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = question.trim()
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

  return (
    <main className="shell">
      <header className="masthead">
        <a className="wordmark" href="/" aria-label="E3SM Assist home"><span className="mark">E3</span>SM-ASSIST</a>
        <p>Scientific grounding for Earth system questions</p>
        <span className="status"><i /> Research mode</span>
      </header>

      <section className={`stage ${response ? 'has-response' : ''}`} aria-live="polite">
        {!response && !loading && !error && <div className="welcome">
          <p className="eyebrow">E3SM knowledge assistant</p>
          <h1>Ask into the<br /><em>Earth system.</em></h1>
          <p className="intro">Get a clear, source-linked answer from E3SM documentation and research material.</p>
        </div>}

        {loading && <div className="thinking"><span className="orb" /><p>Tracing the evidence<span className="ellipsis">...</span></p></div>}
        {error && <div className="error" role="alert"><strong>Unable to get an answer.</strong><p>{error}</p></div>}

        {response && <article className="answer-card">
          <div className="answer-topline"><span className="eyebrow">E3SM-ASSIST</span>{response.insufficient_evidence && <span className="caution">Limited evidence</span>}</div>
          <div className="answer-text">{response.answer}</div>
          {response.citations.length > 0 && <section className="citations"><p>Sources</p><div>{response.citations.map((citation, index) => {
            const url = citationUrl(citation)
            const label = citationLabel(citation, index)
            return url ? <a key={`${url}-${index}`} href={url} target="_blank" rel="noreferrer">{label} <span>↗</span></a> : <span key={`${label}-${index}`}>{label}</span>
          })}</div></section>}
          <EvidencePanel response={response} />
          <DebugPanel response={response} />
        </article>}
      </section>

      <section className="query-area">
        <form onSubmit={submit}>
          <label className="sr-only" htmlFor="question">Ask E3SM-ASSIST a question</label>
          <textarea id="question" rows={2} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question about E3SM..." />
          <button type="submit" disabled={!question.trim() || loading} aria-label="Send question">{loading ? '· · ·' : '↑'}</button>
        </form>
        <div className="starters" aria-label="Example questions">
          {starters.map((starter) => <button key={starter} type="button" onClick={() => setQuestion(starter)}>{starter}</button>)}
        </div>
      </section>
      <footer>Answers are grounded in retrieved material. Verify details in the linked sources.</footer>
    </main>
  )
}
