import { useState, useRef, useEffect } from 'react'
import { ChatInterface } from './components/ChatInterface'
import { IngestPanel } from './components/IngestPanel'
import { Header } from './components/Header'
import { StatusBar } from './components/StatusBar'
import { QueryResponse } from './types'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'ingest'>('chat')
  const [chatHistory, setChatHistory] = useState<Array<{
    role: 'user' | 'assistant'
    content: string
    sources?: QueryResponse['sources']
    timestamp: Date
  }>>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [systemStatus, setSystemStatus] = useState<{
    qdrant: boolean
    ollama: boolean
    embeddings: boolean
  }>({ qdrant: false, ollama: false, embeddings: false })

  // Check system status on mount
  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000) // Check every 30s
    return () => clearInterval(interval)
  }, [])

  const checkHealth = async () => {
    try {
      const response = await fetch('/api/v1/health')
      if (response.ok) {
        const data = await response.json()
        setSystemStatus({
          qdrant: data.services?.qdrant?.status === 'healthy',
          ollama: data.services?.ollama?.status === 'healthy',
          embeddings: data.services?.embeddings?.status === 'healthy',
        })
      }
    } catch (e) {
      console.error('Health check failed:', e)
    }
  }

  const handleQuery = async (question: string) => {
    setIsLoading(true)
    setError(null)

    // Add user message
    setChatHistory(prev => [...prev, {
      role: 'user',
      content: question,
      timestamp: new Date()
    }])

    try {
      const response = await fetch('/api/v1/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, top_k: 5 })
      })

      if (!response.ok) {
        throw new Error('Query failed')
      }

      const data: QueryResponse = await response.json()

      // Add assistant response
      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        timestamp: new Date()
      }])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Query failed')
      // Remove the user message if query failed
      setChatHistory(prev => prev.slice(0, -1))
    } finally {
      setIsLoading(false)
    }
  }

  const handleIngest = async (files: File[], urls: string[]) => {
    // Ingestion logic will be handled by IngestPanel
    // Refresh stats after ingestion
    setTimeout(checkHealth, 2000)
  }

  return (
    <div className="app">
      <Header />
      
      <StatusBar status={systemStatus} />
      
      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          Chat
        </button>
        <button 
          className={`tab ${activeTab === 'ingest' ? 'active' : ''}`}
          onClick={() => setActiveTab('ingest')}
        >
          Ingestar
        </button>
      </div>

      <main className="content">
        {activeTab === 'chat' ? (
          <ChatInterface
            chatHistory={chatHistory}
            onQuery={handleQuery}
            isLoading={isLoading}
            error={error}
          />
        ) : (
          <IngestPanel onIngest={handleIngest} />
        )}
      </main>
    </div>
  )
}

export default App