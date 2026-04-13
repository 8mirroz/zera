// Embedding cache implementation — in-memory with JSONL persistence

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { EmbeddingConfig } from '../config/types.js';
import { EmbeddingCache, EmbeddingCacheEntry } from '../types.js';
import { createLogger, Logger } from '../utils/logger.js';

class EmbeddingCacheImpl implements EmbeddingCache {
  private store: Map<string, EmbeddingCacheEntry>;
  private log: Logger;

  constructor(
    private config: EmbeddingConfig,
    private cacheConfig: { enabled: boolean; cacheFile: string; maxEntries: number; ttl: number },
  ) {
    this.store = new Map();
    this.log = createLogger('embedding-cache');
  }

  get(key: string): EmbeddingCacheEntry | undefined {
    if (!this.cacheConfig.enabled) return undefined;

    const entry = this.store.get(key);
    if (!entry) return undefined;

    // Check TTL
    if (this.cacheConfig.ttl > 0) {
      const age = Date.now() - entry.timestamp;
      if (age > this.cacheConfig.ttl) {
        this.store.delete(key);
        return undefined;
      }
    }

    return entry;
  }

  set(key: string, entry: EmbeddingCacheEntry): void {
    if (!this.cacheConfig.enabled) return;

    // Evict if at capacity
    if (this.store.size >= this.cacheConfig.maxEntries) {
      this.evictOldest();
    }

    this.store.set(key, entry);
  }

  has(key: string): boolean {
    return this.get(key) !== undefined;
  }

  size(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  persist(): void {
    if (!this.cacheConfig.enabled) return;

    try {
      const dir = dirname(this.cacheConfig.cacheFile);
      if (!existsSync(dir)) {
        mkdirSync(dir, { recursive: true });
      }

      const entries: Array<{ key: string; entry: EmbeddingCacheEntry }> = [];
      for (const [key, entry] of this.store.entries()) {
        entries.push({ key, entry });
      }

      writeFileSync(this.cacheConfig.cacheFile, JSON.stringify(entries), 'utf-8');
      this.log.info(`Persisted ${entries.length} cache entries`);
    } catch (err) {
      this.log.error(`Failed to persist cache: ${err}`);
    }
  }

  load(): void {
    if (!this.cacheConfig.enabled) return;

    try {
      if (!existsSync(this.cacheConfig.cacheFile)) {
        this.log.debug('Cache file not found, starting empty');
        return;
      }

      const data = readFileSync(this.cacheConfig.cacheFile, 'utf-8');
      const entries: Array<{ key: string; entry: EmbeddingCacheEntry }> = JSON.parse(data);

      for (const { key, entry } of entries) {
        // Check TTL on load
        if (this.cacheConfig.ttl > 0) {
          const age = Date.now() - entry.timestamp;
          if (age > this.cacheConfig.ttl) continue;
        }

        this.store.set(key, entry);
      }

      this.log.info(`Loaded ${this.store.size} cache entries`);
    } catch (err) {
      this.log.error(`Failed to load cache: ${err}`);
    }
  }

  private evictOldest(): void {
    let oldestKey: string | undefined;
    let oldestTime = Infinity;

    for (const [key, entry] of this.store.entries()) {
      if (entry.timestamp < oldestTime) {
        oldestTime = entry.timestamp;
        oldestKey = key;
      }
    }

    if (oldestKey) {
      this.store.delete(oldestKey);
    }
  }
}

export function createEmbeddingCache(
  config: EmbeddingConfig,
  cacheConfig: { enabled: boolean; cacheFile: string; maxEntries: number; ttl: number },
): EmbeddingCache {
  const cache = new EmbeddingCacheImpl(config, cacheConfig);
  cache.load();
  return cache;
}
