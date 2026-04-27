export interface Source {
  text: string
  source: string
  title: string
  score: number
}

export interface QueryResponse {
  answer: string
  sources: Source[]
  query: string
  latency_ms: number
  success: boolean
  error?: string
}

export interface IngestResponse {
  total_chunks: number
  total_sources: number
  success_count: number
  error_count: number
  results: IngestResult[]
}

export interface IngestResult {
  source: string
  type: 'file' | 'url'
  success: boolean
  chunks_indexed: number
  message: string
}

export interface HealthResponse {
  status: string
  timestamp: string
  services: {
    qdrant: ServiceHealth
    ollama: ServiceHealth
    embeddings: ServiceHealth
  }
  overall: string
}

export interface ServiceHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  latency_ms: number
  message: string
}