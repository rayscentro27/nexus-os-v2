// @vitest-environment jsdom
import React from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, cleanup } from '@testing-library/react'

const api = vi.hoisted(() => ({
  listResearchRoomsLive: vi.fn(),
  getResearchRoomLive: vi.fn(),
  createResearchRoomLive: vi.fn(),
  addResearchRoomSourceLive: vi.fn(),
  askAlphaLive: vi.fn(),
  scoreResearchRoomLive: vi.fn(),
  promoteResearchRoomLive: vi.fn(),
}))

vi.mock('../src/lib/researchRoomApi', () => api)

import ResearchRoomWorkspace from '../src/components/ResearchRoomWorkspace.jsx'

const room = {
  room_id: 'room_chat_test',
  title: 'Chat test room',
  messages: [],
  sources: [{ source_id: 'source_1', title: 'Admira source', domain: 'www.getadmira.com', retrieval_status: 'RETRIEVED' }],
}

beforeEach(() => {
  api.listResearchRoomsLive.mockResolvedValue({ rooms: [room] })
  api.getResearchRoomLive.mockResolvedValue({ room })
  api.askAlphaLive.mockReset()
})

afterEach(() => cleanup())

describe('Research Room conversation UI', () => {
  it('shows the typed question immediately on Send and calls live Alpha once', async () => {
    let resolveAlpha
    api.askAlphaLive.mockReturnValue(new Promise((resolve) => { resolveAlpha = resolve }))
    render(<ResearchRoomWorkspace />)

    const input = await screen.findByTestId('chat-composer-input')
    const question = 'What does Admira do, and how could it help Nexus Marketing and Creative?'
    fireEvent.change(input, { target: { value: question } })
    fireEvent.click(screen.getByTestId('chat-composer-submit'))

    expect(screen.getByText(question)).toBeTruthy()
    expect(screen.getByTestId('alpha-loading-message').textContent).toContain('Thinking')
    expect(input.value).toBe('')
    expect(api.askAlphaLive).toHaveBeenCalledTimes(1)
    expect(api.askAlphaLive).toHaveBeenCalledWith(room.room_id, question)

    resolveAlpha({
      status: 'OK',
      room_id: room.room_id,
      alpha_message: {
        message_id: 'msg_alpha_test',
        room_id: room.room_id,
        author: 'ALPHA',
        content: 'Admira provides marketing attribution and creative intelligence [1].',
        source_refs: ['source_1'],
        metadata: { grounded: true },
      },
    })
    await waitFor(() => expect(screen.getByText(/Admira provides marketing attribution/)).toBeTruthy())
    expect(screen.getByText(question)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '1' }))
    expect(screen.getByTestId('citation-popover-modal').textContent).toContain('www.getadmira.com')
  })

  it('keeps the question visible and displays a bounded error when Alpha fails', async () => {
    api.askAlphaLive.mockRejectedValue(new Error('ALPHA_UNAVAILABLE'))
    render(<ResearchRoomWorkspace />)

    const input = await screen.findByTestId('chat-composer-input')
    const question = 'Summarize the attached sources.'
    fireEvent.change(input, { target: { value: question } })
    fireEvent.click(screen.getByTestId('chat-composer-submit'))

    expect(await screen.findByText('ALPHA_UNAVAILABLE')).toBeTruthy()
    expect(screen.getByText(question)).toBeTruthy()
    expect(api.askAlphaLive).toHaveBeenCalledTimes(1)
  })
})
