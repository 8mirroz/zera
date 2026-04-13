// Core domain types for LightRAG system

export interface Document {
  id: string;
  content: string;
  metadata: Record<string, unknown>;
  createdAt: number;
  updatedAt: number;
}

export interface Chunk {
  id: string;
  documentId: string;
  content: string;
  index: number;
  tokenCount: number;
  metadata: Record<string, unknown>;
}

export interface Embedding {
  chunkId: string;
  vector: number[];
  model: string;
  dimensions: number;
}

export interface RetrievalResult {
  chunk: Chunk;
  score: number;
  rank: number;
}

export interface QueryContext {
  query: string;
  topK: number;
  filters?: Record<string, unknown>;
  debug: boolean;
}

export interface QueryResponse {
  answer: string;
  results: RetrievalResult[];
  latency: LatencyMetrics;
  debugInfo?: DebugInfo;
}

export interface LatencyMetrics {
  embeddingMs: number;
  retrievalMs: number;
  generationMs: number;
  totalMs: number;
}

export interface DebugInfo {
  retrievedChunks: Chunk[];
  scores: number[];
  promptPreview?: string;
  cacheHit?: boolean;
}

export interface IngestResult {
  documentId: string;
  chunksCreated: number;
  embeddingsGenerated: number;
  latency: number;
}

export interface EmbeddingCacheEntry {
  vector: number[];
  model: string;
  timestamp: number;
}

export interface EmbeddingCache {
  get(key: string): EmbeddingCacheEntry | undefined;
  set(key: string, entry: EmbeddingCacheEntry): void;
  has(key: string): boolean;
  size(): number;
  clear(): void;
  persist(): void;
  load(): void;
}
