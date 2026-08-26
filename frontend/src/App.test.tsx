import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

vi.mock('./api', () => ({
  queryAssistant: vi.fn(),
  citationLabel: () => 'Reference',
  citationUrl: () => 'https://example.org/reference',
}))

afterEach(() => {
  cleanup()
})

describe('App', () => {
  it('renders a source metadata object as curated evidence without rendering an object child', async () => {
    const { queryAssistant } = await import('./api')
    vi.mocked(queryAssistant).mockResolvedValue({
      answer: 'A grounded answer.', citations: [], route: 'documentation', insufficient_evidence: false,
      generation_mode: 'llm',
      evidence: [{ content: 'Retrieved context.', sourceLabel: 'E3SM documentation', sourceUrl: 'https://example.org/docs', score: 0.82, coverage: 0.5 }],
    })
    render(<App />)
    const input = screen.getByLabelText('Ask E3SM-ASSIST a question')
    fireEvent.change(input, { target: { value: 'Question' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }))
    expect(await screen.findByText('A grounded answer.')).toBeTruthy()
    expect(screen.getByText('LLM response')).toBeTruthy()
    expect(screen.getByText('1 retrieved')).toBeTruthy()
    screen.getByText('Evidence').click()
    expect(screen.getByText(/E3SM documentation/)).toBeTruthy()
    expect(screen.getByText(/retrieval score 0.820/)).toBeTruthy()
    expect(screen.getByText(/50% lexical coverage/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'What do evidence scores mean?' }))
    const scoreHelp = screen.getByRole('note').textContent
    expect(scoreHelp).toContain('Retrieval score is a relative relevance value')
    expect(scoreHelp).toContain('Lexical coverage is the percentage')
  })

  it('submits a question when Enter is pressed', async () => {
    const { queryAssistant } = await import('./api')
    vi.mocked(queryAssistant).mockResolvedValue({
      answer: 'A grounded answer.', citations: [], route: 'documentation', insufficient_evidence: false,
      evidence: [],
    })
    render(<App />)
    const input = screen.getByLabelText('Ask E3SM-ASSIST a question')
    fireEvent.change(input, { target: { value: 'Question' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(queryAssistant).toHaveBeenCalledWith('Question')
  })

  it('submits a grouped example question and closes the dialog', async () => {
    const { queryAssistant } = await import('./api')
    vi.mocked(queryAssistant).mockResolvedValue({
      answer: 'The grid guide documents aliases and resolutions.', citations: [], evidence: [],
    })
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Explore example questions' }))
    expect(screen.getByRole('dialog', { name: 'Example questions' })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Where are grid aliases and resolutions documented?' }))

    const input = screen.getByLabelText('Ask E3SM-ASSIST a question') as HTMLTextAreaElement
    expect(input.value).toBe('Where are grid aliases and resolutions documented?')
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(queryAssistant).toHaveBeenCalledWith('Where are grid aliases and resolutions documented?')
    expect(await screen.findByText('The grid guide documents aliases and resolutions.')).toBeTruthy()
  })
})
