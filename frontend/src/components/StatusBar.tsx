import './StatusBar.css'

interface StatusBarProps {
  status: {
    qdrant: boolean
    ollama: boolean
    embeddings: boolean
  }
}

export function StatusBar({ status }: StatusBarProps) {
  return (
    <div className="status-bar">
      <div className="status-item">
        <span className={`status-dot ${status.qdrant ? 'healthy' : 'unhealthy'}`}></span>
        <span>Qdrant</span>
      </div>
      <div className="status-item">
        <span className={`status-dot ${status.ollama ? 'healthy' : 'unhealthy'}`}></span>
        <span>Ollama</span>
      </div>
      <div className="status-item">
        <span className={`status-dot ${status.embeddings ? 'healthy' : 'unhealthy'}`}></span>
        <span>Embeddings</span>
      </div>
    </div>
  )
}