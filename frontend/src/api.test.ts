import { describe, expect, it } from 'vitest'
import { normalizeQueryResponse } from './api'

describe('normalizeQueryResponse', () => {
  it('prefers canonical retrieved_evidence and safely flattens source metadata', () => {
    const response = normalizeQueryResponse({
      answer: 'Grounded answer.',
      route: 'literature',
      retrieved_evidence: [{
        title: 'Canonical passage', content: 'A retrieved passage.', score: 0.82,
        source: { title: 'E3SM reference guide', url: 'https://example.org/guide' },
      }],
      evidence: [{ content: 'Legacy passage that must not be shown.', source: 'old source' }],
      citations: [{ source: { title: 'Reference', url: 'https://example.org/ref' } }],
    })

    expect(response.evidence).toEqual([{
      title: 'Canonical passage', content: 'A retrieved passage.', score: 0.82,
      sourceLabel: 'E3SM reference guide', sourceUrl: 'https://example.org/guide',
    }])
    expect(response.citations).toHaveLength(1)
  })
})
