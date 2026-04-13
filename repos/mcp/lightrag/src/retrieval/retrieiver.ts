// Retriever — cosine similarity + hybrid keyword retrieval

import { RetrievalConfig } from '../config/types.js';
import { Chunk, Embedding, RetrievalResult, QueryContext } from '../types.js';
import { createLogger, Logger } from '../utils/logger.js';
import { KeywordIndex } from '../store/index.js';

export interface Retriever {
  retrieve(query: string, embeddings: Map<string, number[]>, config: QueryContext): Promise<RetrievalResult[]>;
}

export class VectorRetriever implements Retriever {
  private log: Logger;

  constructor(private config: RetrievalConfig) {
    this.log = createLogger('retriever');
  }

  async retrieve(
    query: string,
    chunkEmbeddings: Map<string, number[]>,
    context: QueryContext,
  ): Promise<RetrievalResult[]> {
    const startTime = Date.now();

    const { topK, minScore, hybrid } = this.config;

    if (chunkEmbeddings.size === 0) {
      this.log.warn('No embeddings in index');
      return [];
    }

    // Calculate cosine similarity between query and each chunk
    const scores: Array<{ chunkId: string; score: number }> = [];

    for (const [chunkId, chunkVector] of chunkEmbeddings.entries()) {
      const score = cosineSimilarity(query, chunkVector);
      if (score >= minScore) {
        scores.push({ chunkId, score });
      }
    }

    // Sort by score descending
    scores.sort((a, b) => b.score - a.score);

    // Take top-k
    const topResults = scores.slice(0, topK);

    const results: RetrievalResult[] = topResults.map((result, index) => ({
      chunk: { id: result.chunkId } as any, // Temporary placeholder, will be populated by pipeline
      score: result.score,
      rank: index + 1,
    }));

    const duration = Date.now() - startTime;
    this.log.debug(`Retrieved ${results.length} results in ${duration}ms`, {
      query: query.substring(0, 50),
      topScore: results[0]?.score,
      avgScore: results.length > 0
        ? results.reduce((sum, r) => sum + r.score, 0) / results.length
        : 0,
    });

    return results;
  }
}

/**
 * Hybrid retriever — combines vector similarity + keyword matching
 */
export class HybridRetriever implements Retriever {
  private log: Logger;
  private vectorRetriever: VectorRetriever;

  constructor(
    private config: RetrievalConfig,
    private keywordIndex: KeywordIndex,
  ) {
    this.log = createLogger('hybrid-retriever');
    this.vectorRetriever = new VectorRetriever(config);
  }

  async retrieve(
    query: string,
    chunkEmbeddings: Map<string, number[]>,
    context: QueryContext,
  ): Promise<RetrievalResult[]> {
    const startTime = Date.now();
    const { topK, keywordWeight, maxKeywordResults } = this.config;

    // Get vector results
    const vectorResults = await this.vectorRetriever.retrieve(query, chunkEmbeddings, context);

    // Get keyword results
    const keywordResults = this.keywordIndex.search(query, maxKeywordResults);

    // Normalize scores to [0, 1] range
    const maxVectorScore = vectorResults.length > 0 ? Math.max(...vectorResults.map((r) => r.score)) : 1;
    const maxKeywordScore = keywordResults.length > 0 ? Math.max(...keywordResults.map((r) => r.score)) : 1;

    // Create lookup maps
    const vectorScoreMap = new Map(vectorResults.map((r) => [r.chunk?.id, r.score / maxVectorScore]));
    const keywordScoreMap = new Map(keywordResults.map((r) => [r.docId, r.score / maxKeywordScore]));

    // Merge results
    const allIds = new Set([
      ...vectorResults.map((r) => r.chunk?.id),
      ...keywordResults.map((r) => r.docId),
    ]);

    const merged: Array<{ id: string; score: number }> = [];

    for (const id of allIds) {
      if (!id) continue;
      const vScore = vectorScoreMap.get(id) || 0;
      const kScore = keywordScoreMap.get(id) || 0;

      // Weighted combination
      const combinedScore =
        (1 - keywordWeight) * vScore +
        keywordWeight * kScore;

      merged.push({ id, score: combinedScore });
    }

    // Sort and take top-k
    merged.sort((a, b) => b.score - a.score);
    const topResults = merged.slice(0, topK);

    const results: RetrievalResult[] = topResults.map((result, index) => ({
      chunk: { id: result.id } as any, // Temporary placeholder, will be populated by pipeline
      score: result.score,
      rank: index + 1,
    }));

    const duration = Date.now() - startTime;
    this.log.debug(`Hybrid retrieval: ${results.length} results in ${duration}ms`, {
      vectorResults: vectorResults.length,
      keywordResults: keywordResults.length,
      mergedResults: merged.length,
    });

    return results;
  }
}

/**
 * Cosine similarity between a text query (hashed embedding) and a vector
 * For the hash-based local embeddings, we use a simplified approach
 */
export function cosineSimilarity(query: string, vector: number[]): number {
  // Create a simple query vector using the same hashing approach
  const queryVector = hashVector(query, vector.length);

  let dotProduct = 0;
  let queryNorm = 0;
  let vectorNorm = 0;

  for (let i = 0; i < vector.length; i++) {
    const q = queryVector[i] || 0;
    const v = vector[i] || 0;

    dotProduct += q * v;
    queryNorm += q * q;
    vectorNorm += v * v;
  }

  if (queryNorm === 0 || vectorNorm === 0) return 0;

  return dotProduct / (Math.sqrt(queryNorm) * Math.sqrt(vectorNorm));
}

/**
 * Create a hash-based vector for text (matches LocalEmbeddingProvider approach)
 */
function hashVector(text: string, dimensions: number): number[] {
  const vector = new Float32Array(dimensions);
  const tokens = text.toLowerCase().split(/\s+/).filter(Boolean);

  for (const token of tokens) {
    let hash = 0;
    for (let i = 0; i < token.length; i++) {
      hash = ((hash << 5) - hash) + token.charCodeAt(i);
      hash |= 0;
    }

    const h1 = Math.abs(hash) % dimensions;
    const h2 = Math.abs(hash * 31) % dimensions;
    const h3 = Math.abs(hash * 37) % dimensions;

    vector[h1]! += 1.0;
    vector[h2]! += 0.5;
    vector[h3]! += 0.25;
  }

  // L2 normalize
  const norm = Math.sqrt(Array.from(vector).reduce((sum, v) => sum + v * v, 0));
  if (norm > 0) {
    for (let i = 0; i < dimensions; i++) {
      vector[i]! /= norm;
    }
  }

  return Array.from(vector);
}

export function createRetriever(
  config: RetrievalConfig,
  keywordIndex?: KeywordIndex,
): Retriever {
  if (config.hybrid && keywordIndex) {
    return new HybridRetriever(config, keywordIndex);
  }
  return new VectorRetriever(config);
}
