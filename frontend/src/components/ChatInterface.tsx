import { useState, useRef, useEffect } from 'react'
import { QueryResponse } from '../types'
import './ChatInterface.css'

interface ChatInterfaceProps {
  chatHistory: Array<{
    role: 'user' | 'assistant'
    content: string
    sources?: QueryResponse['sources']
    timestamp: Date
  }>
  onQuery: (question: string) => void
  isLoading: boolean
  error: string | null
}

export function ChatInterface({ chatHistory, onQuery, isLoading, error }: ChatInterfaceProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [chatHistory])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onQuery(input.trim())
      setInput('')
    }
  }

  const examples = [
    '¿De qué trata el juego?',
    '¿Qué es la especia Melange?',
    'Dime sobre las Casas',
  ]

  return (
    <div className="chat-interface">
      <div className="messages">
        {chatHistory.length === 0 && (
          <div className="welcome">
            <h2>¡Bienvenido a Dune Bot!</h2>
            <p>Pregúntame sobre el universo Dune, el juego, o cualquier cosa relacionada.</p>
            <div className="examples">
              <span>Ejemplos:</span>
              {examples.map((example, i) => (
                <button key={i} onClick={() => onQuery(example)} className="example-btn">
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

        {chatHistory.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className="message-content">
              {msg.content}
            </div>
            {msg.sources && msg.sources.length > 0 && (
              <div className="sources">
                <span className="sources-label">📚 Fuentes:</span>
                {msg.sources.slice(0, 3).map((source, j) => (
                  <div key={j} className="source-item">
                    <span className="source-title">{source.title || source.source}</span>
                    <span className="source-score">{(source.score * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            )}
            <div className="message-time">
              {msg.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message assistant loading">
            <div className="message-content">
              <span className="loading-dot"></span>
              <span className="loading-dot"></span>
              <span className="loading-dot"></span>
            </div>
          </div>
        )}

        {error && (
          <div className="error-message">
            ❌ {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="input-form">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe tu pregunta..."
          disabled={isLoading}
          className="input-field"
        />
        <button type="submit" disabled={!input.trim() || isLoading} className="send-btn">
          Enviar
        </button>
      </form>
    </div>
  )
}