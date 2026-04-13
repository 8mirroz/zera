// Configuration types

export interface ChunkingConfig {
  /** Target chunk size in tokens (256-1024) */
  chunkSize: number;
  /** Overlap between chunks in tokens */
  chunkOverlap: number;
  /** Minimum chunk size before merging with neighbor */
  minChunkSize: number;
  /** Use semantic boundary detection */
  semanticBoundaries: boolean;
}

export interface EmbeddingConfig {
  /** Provider type: 'local' | 'openai' | 'gemini' */
  provider: 'local' | 'openai' | 'gemini';
  /** Model name within provider */
  model: string;
  /** Vector dimensions */
  dimensions: number;
  /** API key (for API providers) */
  apiKey?: string;
  /** API endpoint (for local Ollama/etc) */
  endpoint?: string;
  /** Batch size for embedding generation */
  batchSize: number;
}

export interface StorageConfig {
  /** Storage backend: 'jsonl' | 'sqlite' */
  backend: 'jsonl' | 'sqlite';
  /** Data directory path */
  dataDir: string;
  /** Maximum documents in memory before flushing */
  flushThreshold: number;
  /** Enable compression for JSONL */
  compression: boolean;
}

export interface RetrievalConfig {
  /** Number of top results to return */
  topK: number;
  /** Minimum similarity threshold (0-1) */
  minScore: number;
  /** Enable hybrid retrieval (keyword + vector) */
  hybrid: boolean;
  /** Keyword weight in hybrid mode (0-1) */
  keywordWeight: number;
  /** Maximum results for keyword matching */
  maxKeywordResults: number;
}

export interface GenerationConfig {
  /** Provider: 'openai' | 'gemini' | 'ollama' | 'qwen' */
  provider: 'openai' | 'gemini' | 'ollama' | 'qwen';
  /** Model name */
  model: string;
  /** API key (for API providers) */
  apiKey?: string;
  /** API endpoint (for local models) */
  endpoint?: string;
  /** Maximum tokens in response */
  maxTokens: number;
  /** Temperature for generation */
  temperature: number;
  /** System prompt template */
  systemPrompt?: string;
}

export interface CacheConfig {
  /** Enable embedding cache */
  enabled: boolean;
  /** Cache file path */
  cacheFile: string;
  /** Maximum cache entries */
  maxEntries: number;
  /** Cache TTL in milliseconds (0 = no expiry) */
  ttl: number;
}

export interface MemoryConfig {
  /** Maximum RAM usage in MB before triggering cleanup */
  maxMemoryMB: number;
  /** Enable lazy indexing */
  lazyIndexing: boolean;
  /** Auto-rebuild index after N ingests */
  autoRebuildThreshold: number;
}

export interface LightRagConfig {
  chunking: ChunkingConfig;
  embedding: EmbeddingConfig;
  storage: StorageConfig;
  retrieval: RetrievalConfig;
  generation: GenerationConfig;
  cache: CacheConfig;
  memory: MemoryConfig;
  /** Enable debug logging */
  debug: boolean;
  /** Log level */
  logLevel: 'debug' | 'info' | 'warn' | 'error';
}

export const DEFAULT_CONFIG: LightRagConfig = {
  chunking: {
    chunkSize: 512,
    chunkOverlap: 64,
    minChunkSize: 128,
    semanticBoundaries: true,
  },
  embedding: {
    provider: 'local',
    model: 'bge-small',
    dimensions: 384,
    batchSize: 32,
  },
  storage: {
    backend: 'jsonl',
    dataDir: './data',
    flushThreshold: 100,
    compression: false,
  },
  retrieval: {
    topK: 5,
    minScore: 0.3,
    hybrid: true,
    keywordWeight: 0.3,
    maxKeywordResults: 20,
  },
  generation: {
    provider: 'ollama',
    model: 'qwen2.5-coder:7b',
    maxTokens: 2048,
    temperature: 0.1,
  },
  cache: {
    enabled: true,
    cacheFile: './data/cache/embeddings.json',
    maxEntries: 10000,
    ttl: 86400000, // 24 hours
  },
  memory: {
    maxMemoryMB: 512,
    lazyIndexing: true,
    autoRebuildThreshold: 50,
  },
  debug: false,
  logLevel: 'info',
};
