// Embedding provider interface and implementations

import { EmbeddingConfig } from '../config/types.js';
import { createLogger, Logger } from '../utils/logger.js';

export interface EmbeddingProvider {
  embed(texts: string[]): Promise<number[][]>;
  getDimensions(): number;
}

/**
 * Local embedding provider — lightweight simulated embeddings
 * For production: integrate with bge-small, e5-small, or nomic-embed via Ollama
 */
export class LocalEmbeddingProvider implements EmbeddingProvider {
  private log: Logger;
  private dimensions: number;

  constructor(private config: EmbeddingConfig) {
    this.log = createLogger('local-embeddings');
    this.dimensions = config.dimensions;
  }

  async embed(texts: string[]): Promise<number[][]> {
    // For local embeddings, we use a simple hashing trick + TF-IDF-like approach
    // In production, replace this with actual local model inference (Ollama/MLX)
    const results: number[][] = [];

    for (const text of texts) {
      const vector = this.hashEmbedding(text);
      results.push(vector);
    }

    return results;
  }

  getDimensions(): number {
    return this.dimensions;
  }

  /**
   * Simple hash-based embedding for development/testing
   * This produces deterministic vectors for the same input
   * Replace with actual model inference in production
   */
  private hashEmbedding(text: string): number[] {
    const vector = new Float32Array(this.dimensions);
    const tokens = text.toLowerCase().split(/\s+/).filter(Boolean);

    // Hash each token into vector dimensions
    for (const token of tokens) {
      let hash = 0;
      for (let i = 0; i < token.length; i++) {
        hash = ((hash << 5) - hash) + token.charCodeAt(i);
        hash |= 0;
      }

      // Use multiple hash functions to spread across dimensions
      const h1 = Math.abs(hash) % this.dimensions;
      const h2 = Math.abs(hash * 31) % this.dimensions;
      const h3 = Math.abs(hash * 37) % this.dimensions;

      vector[h1]! += 1.0;
      vector[h2]! += 0.5;
      vector[h3]! += 0.25;
    }

    // L2 normalize
    const norm = Math.sqrt(Array.from(vector).reduce((sum, v) => sum + v * v, 0));
    if (norm > 0) {
      for (let i = 0; i < this.dimensions; i++) {
        vector[i]! /= norm;
      }
    }

    return Array.from(vector);
  }
}

/**
 * API embedding provider — OpenAI / Gemini compatible
 */
export class ApiEmbeddingProvider implements EmbeddingProvider {
  private log: Logger;
  private endpoint: string;
  private headers: Record<string, string>;

  constructor(private config: EmbeddingConfig) {
    this.log = createLogger('api-embeddings');

    if (config.provider === 'openai') {
      this.endpoint = config.endpoint || 'https://api.openai.com/v1/embeddings';
      this.headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`,
      };
    } else if (config.provider === 'gemini') {
      this.endpoint = config.endpoint ||
        `https://generativelanguage.googleapis.com/v1beta/models/${config.model}:embedContent?key=${config.apiKey}`;
      this.headers = {
        'Content-Type': 'application/json',
      };
    } else {
      throw new Error(`Unsupported API provider: ${config.provider}`);
    }
  }

  async embed(texts: string[]): Promise<number[][]> {
    const results: number[][] = [];

    // Process in batches
    const batchSize = this.config.batchSize;
    for (let i = 0; i < texts.length; i += batchSize) {
      const batch = texts.slice(i, i + batchSize);

      if (this.config.provider === 'openai') {
        const vectors = await this.embedOpenAI(batch);
        results.push(...vectors);
      } else if (this.config.provider === 'gemini') {
        for (const text of batch) {
          const vector = await this.embedGemini(text);
          results.push(vector);
        }
      }
    }

    return results;
  }

  getDimensions(): number {
    return this.config.dimensions;
  }

  private async embedOpenAI(texts: string[]): Promise<number[][]> {
    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        model: this.config.model,
        input: texts,
      }),
    });

    if (!response.ok) {
      throw new Error(`OpenAI embedding API error: ${response.status} ${response.statusText}`);
    }

    const data: { data: Array<{ embedding: number[] }> } = await response.json();
    return data.data.map((item) => item.embedding);
  }

  private async embedGemini(text: string): Promise<number[]> {
    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        content: {
          parts: [{ text }],
        },
      }),
    });

    if (!response.ok) {
      throw new Error(`Gemini embedding API error: ${response.status} ${response.statusText}`);
    }

    const data: { embedding: { values: number[] } } = await response.json();
    return data.embedding.values;
  }
}
