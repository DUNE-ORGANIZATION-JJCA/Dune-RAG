import { useState, useRef } from 'react'
import { IngestResponse } from '../types'
import './IngestPanel.css'

interface IngestPanelProps {
  onIngest: (files: File[], urls: string[]) => void
}

export function IngestPanel({ onIngest }: IngestPanelProps) {
  const [files, setFiles] = useState<File[]>([])
  const [urls, setUrls] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<IngestResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files
    if (selectedFiles) {
      setFiles(prev => [...prev, ...Array.from(selectedFiles)])
    }
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async () => {
    if (files.length === 0 && !urls.trim()) {
      setError('Selecciona archivos o introduce URLs')
      return
    }

    setIsLoading(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      
      for (const file of files) {
        formData.append('files', file)
      }
      
      if (urls.trim()) {
        formData.append('urls', urls)
      }

      const response = await fetch('/api/v1/ingest', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('Ingest failed')
      }

      const data: IngestResponse = await response.json()
      setResult(data)
      
      if (data.success_count > 0) {
        setFiles([])
        setUrls('')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ingest failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="ingest-panel">
      <div className="ingest-section">
        <h3>📄 Subir archivos</h3>
        <p>PDF, DOCX, PPTX, TXT</p>
        
        <div 
          className="drop-zone"
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.pptx,.txt"
            onChange={handleFileSelect}
            hidden
          />
          <span>📁 Haz clic o arrastra archivos aquí</span>
        </div>

        {files.length > 0 && (
          <div className="file-list">
            {files.map((file, i) => (
              <div key={i} className="file-item">
                <span>{file.name}</span>
                <button onClick={() => removeFile(i)}>✕</button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="ingest-section">
        <h3>🔗 URLs</h3>
        <p>Una o varias URLs separadas por comas</p>
        
        <textarea
          value={urls}
          onChange={(e) => setUrls(e.target.value)}
          placeholder="https://example.com, https://otro.com"
          rows={3}
        />
      </div>

      <button 
        onClick={handleSubmit} 
        disabled={isLoading || (files.length === 0 && !urls.trim())}
        className="ingest-btn"
      >
        {isLoading ? '⏳ Procesando...' : '📥 Ingestar'}
      </button>

      {error && (
        <div className="error-message">{error}</div>
      )}

      {result && (
        <div className="result-panel">
          <h4>📊 Resultados</h4>
          <div className="stats">
            <div className="stat">
              <span className="stat-value">{result.total_chunks}</span>
              <span className="stat-label">Chunks</span>
            </div>
            <div className="stat">
              <span className="stat-value">{result.success_count}</span>
              <span className="stat-label">Exitosos</span>
            </div>
            <div className="stat">
              <span className="stat-value">{result.error_count}</span>
              <span className="stat-label">Errores</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}