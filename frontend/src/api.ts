export type SourceMetadata = {
  title?: unknown
  name?: unknown
  source?: unknown
  url?: unknown
  href?: unknown
  uri?: unknown
  [key: string]: unknown
}

export type Citation = {
  title?: unknown
  url?: unknown
  href?: unknown
  source?: unknown
  text?: unknown
  [key: string]: unknown
}

export type Evidence = {
  title?: string
  content?: string
  sourceLabel?: string
  sourceUrl?: string
  score?: number
}

export type QueryResponse = {
  answer: string
  route?: string
  citations: Citation[]
  evidence: Evidence[]
  insufficient_evidence?: boolean
}

type RawQueryResponse = {
  answer?: unknown
  route?: unknown
  citations?: unknown
  retrieved_evidence?: unknown
  evidence?: unknown
  insufficient_evidence?: unknown
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

function text(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined
}

function record(value: unknown): Record<string, unknown> | undefined {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined
}

function sourceDetails(value: unknown): { label?: string; url?: string } {
  const metadata = record(value)
  if (!metadata) return { label: text(value) }
  return {
    label: text(metadata.title) ?? text(metadata.name) ?? text(metadata.source) ?? text(metadata.file_name) ?? text(metadata.path),
    url: text(metadata.url) ?? text(metadata.href) ?? text(metadata.uri),
  }
}

function normalizeEvidence(value: unknown): Evidence | null {
  const item = record(value)
  if (!item) return null
  const source = sourceDetails(item.source ?? item.source_metadata ?? item.metadata)
  const score = typeof item.score === 'number' ? item.score : undefined
  return {
    title: text(item.title) ?? text(item.document_title),
    content: text(item.content) ?? text(item.text) ?? text(item.passage) ?? text(item.chunk),
    sourceLabel: source.label,
    sourceUrl: source.url ?? text(item.url),
    score,
  }
}

/** Converts canonical and legacy provider responses into the UI's safe display shape. */
export function normalizeQueryResponse(payload: unknown): QueryResponse {
  const response = record(payload) as RawQueryResponse | undefined
  if (!response) throw new Error('The assistant returned an invalid response.')
  // `retrieved_evidence` is the canonical backend field. Only use legacy evidence when it is absent.
  const rawEvidence = Array.isArray(response.retrieved_evidence) ? response.retrieved_evidence : response.evidence
  return {
    answer: text(response.answer) ?? '',
    route: text(response.route),
    citations: Array.isArray(response.citations) ? response.citations.filter((item): item is Citation => record(item) !== undefined) : [],
    evidence: Array.isArray(rawEvidence) ? rawEvidence.map(normalizeEvidence).filter((item): item is Evidence => item !== null) : [],
    insufficient_evidence: response.insufficient_evidence === true,
  }
}

export async function queryAssistant(question: string): Promise<QueryResponse> {
  const response = await fetch(`${apiBaseUrl}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed (${response.status})`)
  }
  return normalizeQueryResponse(await response.json())
}

export function citationLabel(citation: Citation, index: number) {
  return text(citation.title) ?? sourceDetails(citation.source).label ?? text(citation.text) ?? `Source ${index + 1}`
}

export function citationUrl(citation: Citation) {
  return text(citation.url) ?? text(citation.href) ?? sourceDetails(citation.source).url
}
