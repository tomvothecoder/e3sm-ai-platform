import { afterEach, describe, expect, it, vi } from 'vitest'
import { normalizeQueryResponse, queryAssistant } from './api'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('normalizeQueryResponse', () => {
  it('prefers canonical retrieved_evidence and safely flattens source metadata', () => {
    const response = normalizeQueryResponse({
      answer: 'Grounded answer.',
      route: 'literature',
      generation_mode: 'llm',
      retrieved_evidence: [{
        title: 'Canonical passage', content: 'A retrieved passage.', score: 0.82,
        source: { title: 'E3SM reference guide', url: 'https://example.org/guide' },
      }],
      evidence: [{ content: 'Legacy passage that must not be shown.', source: 'old source' }],
      citations: [{ source: { title: 'Reference', url: 'https://example.org/ref' } }],
    })

    expect(response.evidence).toEqual([{
      title: 'Canonical passage', content: 'A retrieved passage.', score: 0.82,
      sourceLabel: 'E3SM reference guide', sourceUrl: 'https://example.org/guide', coverage: undefined,
      retrievalMode: undefined, lexicalScore: undefined, semanticScore: undefined,
    }])
    expect(response.citations).toHaveLength(1)
    expect(response.generation_mode).toBe('llm')
  })
})

describe('queryAssistant', () => {
  it('sends a valid W3C traceparent and normalizes a successful response', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      answer: 'Grounded answer.',
      retrieved_evidence: [{ content: 'Retrieved passage.', source: 'E3SM docs' }],
    }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(queryAssistant('What is E3SM?')).resolves.toEqual({
      answer: 'Grounded answer.',
      citations: [],
      evidence: [{ content: 'Retrieved passage.', sourceLabel: 'E3SM docs', sourceUrl: undefined, title: undefined, score: undefined, coverage: undefined, retrievalMode: undefined, lexicalScore: undefined, semanticScore: undefined }],
      generation_mode: undefined,
      insufficient_evidence: false,
      route: undefined,
    })

    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit]
    const traceparent = new Headers(options.headers).get('traceparent')
    expect(traceparent).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/)
  })

  it('uses a stable public error and server request ID for non-success responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('internal secret: database unavailable', {
      status: 500,
      headers: { 'X-Request-ID': 'req_abc-123' },
    })))

    await expect(queryAssistant('Question that must not appear in errors')).rejects.toThrow(
      'The assistant request could not be completed. Please try again. Request ID: req_abc-123.',
    )
  })

  it('does not expose server response details when no request ID is supplied', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('sensitive server detail', { status: 400 })))

    await expect(queryAssistant('Question')).rejects.toThrow(
      'The assistant request could not be completed. Please try again.',
    )
  })
})
