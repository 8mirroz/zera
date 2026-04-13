// Embeddings abstraction layer — supports local + API providers

import { EmbeddingConfig } from '../config/types.js';
import { EmbeddingCache, EmbeddingCacheEntry } from '../types.js';
import { createLogger, Logger } from '../utils/logger.js';
import { createEmbeddingCache } from './cache.js';
import { LocalEmbeddingProvider, ApiEmbeddingProvider, EmbeddingProvider } from './provider.js';

export interface EmbeddingResult {
  text: string;
  vector: number[];
  model: string;
  dimensions: number;
  cached: boolean;
}

export interface EmbeddingsService {
  embed(text: string): Promise<EmbeddingResult>;
  embedBatch(texts: string[]): Promise<EmbeddingResult[]>;
  getDimensions(): number;
  getModel(): string;
  getCache(): EmbeddingCache;
}

export class EmbeddingsServiceImpl implements EmbeddingsService {
  private provider: EmbeddingProvider;
  private cache: EmbeddingCache;
  private log: Logger;

  constructor(
    private config: EmbeddingConfig,
    cache: EmbeddingCache,
  ) {
    this.log = createLogger('embeddings');
    this.cache = cache;

    if (config.provider === 'local') {
      this.provider = new LocalEmbeddingProvider(config);
    } else {
      this.provider = new ApiEmbeddingProvider(config);
    }
  }

  async embed(text: string): Promise<EmbeddingResult> {
    const cacheKey = this.getCacheKey(text);

    // Check cache
    const cached = this.cache.get(cacheKey);
    if (cached) {
      this.log.debug(`Cache hit for embedding: ${cacheKey.substring(0, 20)}...`);
      return {
        text,
        vector: cached.vector,
        model: cached.model,
        dimensions: this.config.dimensions,
        cached: true,
      };
    }

    // Generate embedding
    const result = await this.provider.embed([text]);
    const vector = result[0]!;

    // Cache result
    this.cache.set(cacheKey, {
      vector,
      model: this.config.model,
      timestamp: Date.now(),
    });

    return {
      text,
      vector,
      model: this.config.model,
      dimensions: this.config.dimensions,
      cached: false,
    };
  }

  async embedBatch(texts: string[]): Promise<EmbeddingResult[]> {
    const results: EmbeddingResult[] = [];
    const toEmbed: string[] = [];
    const toEmbedIndices: number[] = [];

    // Check cache for each text
    for (let i = 0; i < texts.length; i++) {
      const cacheKey = this.getCacheKey(texts[i]!);
      const cached = this.cache.get(cacheKey);

      if (cached) {
        results.push({
          text: texts[i]!,
          vector: cached.vector,
          model: cached.model,
          dimensions: this.config.dimensions,
          cached: true,
        });
      } else {
        toEmbed.push(texts[i]!);
        toEmbedIndices.push(i);
        results.push(null as any); // placeholder
      }
    }

    // Generate embeddings for uncached texts
    if (toEmbed.length > 0) {
      this.log.debug(`Embedding ${toEmbed.length}/${texts.length} texts (cache miss)`);
      const vectors = await this.provider.embed(toEmbed);

      for (let i = 0; i < toEmbed.length; i++) {
        const vector = vectors[i]!;
        const cacheKey = this.getCacheKey(toEmbed[i]!);

        this.cache.set(cacheKey, {
          vector,
          model: this.config.model,
          timestamp: Date.now(),
        });

        results[toEmbedIndices[i]!] = {
          text: toEmbed[i]!,
          vector,
          model: this.config.model,
          dimensions: this.config.dimensions,
          cached: false,
        };
      }
    }

    return results;
  }

  getDimensions(): number {
    return this.config.dimensions;
  }

  getModel(): string {
    return this.config.model;
  }

  getCache(): EmbeddingCache {
    return this.cache;
  }

  private getCacheKey(text: string): string {
    // Simple hash for cache key
    let hash = 0;
    const str = text.trim().toLowerCase();
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash |= 0;
    }
    return `${this.config.model}:${hash.toString(16)}`;
  }
}

export function createEmbeddingsService(config: EmbeddingConfig): EmbeddingsService {
  const cacheConfig = {
    enabled: true,
    cacheFile: './data/cache/embeddings.json',
    maxEntries: 10000,
    ttl: 86400000,
  };
  const cache = createEmbeddingCache(config, cacheConfig);
  return new EmbeddingsServiceImpl(config, cache);
}
