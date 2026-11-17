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

const room = { room_id: 'room_chat_test', title: 'Chat test room', messages: [], sources: [] }

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

    resolveAlpha({ answer: 'Admira provides marketing attribution and creative intelligence.' })
    await waitFor(() => expect(screen.getByText(/Admira provides marketing attribution/)).toBeTruthy())
    expect(screen.getByText(question)).toBeTruthy()
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
