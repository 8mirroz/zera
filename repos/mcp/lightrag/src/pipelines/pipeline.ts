// Main query pipeline — orchestrates the full RAG flow

import { LightRagConfig } from '../config/types.js';
import {
  Document,
  Chunk,
  Embedding,
  QueryContext,
  QueryResponse,
  RetrievalResult,
  LatencyMetrics,
  DebugInfo,
} from '../types.js';
import { createLogger, Logger } from '../utils/logger.js';
import { chunkDocuments } from '../chunking/chunker.js';
import { EmbeddingsService, createEmbeddingsService } from '../embeddings/service.js';
import { createRetriever, Retriever } from '../retrieval/retrieiver.js';
import { createGenerator, Generator } from '../generation/generator.js';
import { JsonlStorage, StorageAdapter } from '../store/jsonl.js';
import { SqliteStorage } from '../store/sqlite.js';
import { KeywordIndex } from '../store/index.js';

export class LightRagPipeline {
  private log: Logger;
  private storage: StorageAdapter;
  private embeddingsService: EmbeddingsService;
  private retriever: Retriever;
  private generator: Generator;
  private chunkEmbeddings: Map<string, number[]>; // chunkId -> vector
  private keywordIndex: KeywordIndex;

  constructor(private config: LightRagConfig) {
    this.log = createLogger('pipeline', config.debug ? 0 : 1);

    // Initialize storage
    if (config.storage.backend === 'sqlite') {
      this.storage = new SqliteStorage(config.storage);
    } else {
      this.storage = new JsonlStorage(config.storage);
    }

    // Initialize embeddings
    this.embeddingsService = createEmbeddingsService(config.embedding);

    // Initialize retriever
    this.keywordIndex = this.storage.getKeywordIndex();
    this.retriever = createRetriever(config.retrieval, this.keywordIndex);

    // Initialize generator
    this.generator = createGenerator(config.generation);

    // Load existing chunk embeddings from storage
    this.chunkEmbeddings = new Map();
    this.loadChunkEmbeddings();
  }

  /**
   * Ingest a document into the RAG system
   */
  async ingest(content: string, metadata: Record<string, unknown> = {}): Promise<{
    documentId: string;
    chunksCreated: number;
    embeddingsGenerated: number;
    latency: number;
  }> {
    const startTime = Date.now();
    this.log.time('ingest-total');

    // Create document
    const docId = `doc_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    const now = Date.now();
    const document: Document = {
      id: docId,
      content,
      metadata: {
        source: 'manual',
        ...metadata,
      },
      createdAt: now,
      updatedAt: now,
    };

    this.log.info(`Ingesting document: ${docId}`);
    await this.storage.saveDocument(document);

    // Chunk document
    const chunks = chunkDocuments([document], this.config.chunking);
    this.log.info(`Created ${chunks.length} chunks`);

    // Save chunks
    for (const chunk of chunks) {
      await this.storage.saveChunk(chunk);
    }

    // Generate embeddings for chunks
    const chunkTexts = chunks.map((c) => c.content);
    const embeddingResults = await this.embeddingsService.embedBatch(chunkTexts);

    for (let i = 0; i < chunks.length; i++) {
      const chunk = chunks[i]!;
      const embedding = embeddingResults[i]!;

      const emb: Embedding = {
        chunkId: chunk.id,
        vector: embedding.vector,
        model: embedding.model,
        dimensions: embedding.dimensions,
      };

      await this.storage.saveEmbedding(emb);
      this.chunkEmbeddings.set(chunk.id, embedding.vector);
    }

    // Persist cache periodically
    if (this.config.cache.enabled) {
      this.embeddingsService.getCache().persist();
    }

    const latency = this.log.timeEnd('ingest-total');
    this.log.info(`Ingestion complete: ${chunks.length} chunks, ${latency}ms`);

    return {
      documentId: docId,
      chunksCreated: chunks.length,
      embeddingsGenerated: embeddingResults.length,
      latency,
    };
  }

  /**
   * Query the RAG system
   */
  async query(queryText: string, options?: Partial<QueryContext>): Promise<QueryResponse> {
    const startTime = Date.now();
    this.log.time('query-total');

    const context: QueryContext = {
      query: queryText,
      topK: this.config.retrieval.topK,
      filters: options?.filters,
      debug: options?.debug ?? this.config.debug,
    };

    // Step 1: Embed query
    this.log.time('embedding');
    const queryEmbedding = await this.embeddingsService.embed(queryText);
    const embeddingMs = this.log.timeEnd('embedding');

    // Step 2: Retrieve top-k chunks
    this.log.time('retrieval');
    const retrievalResults = await this.retriever.retrieve(
      queryText,
      this.chunkEmbeddings,
      context,
    );
    const retrievalMs = this.log.timeEnd('retrieval');

    // Step 3: Populate chunk data in results
    const allChunks = await this.storage.getAllChunks();
    const chunkMap = new Map(allChunks.map((c) => [c.id, c]));

    for (const result of retrievalResults) {
      const chunk = chunkMap.get(result.chunk.id);
      if (chunk) {
        result.chunk = chunk;
      }
    }

    // Step 4: Generate answer
    this.log.time('generation');
    let answer = '';
    try {
      answer = await this.generator.generate(queryText, retrievalResults);
    } catch (err) {
      this.log.error(`Generation failed: ${err}`);
      answer = `[Generation error: ${err}]\n\nRetrieved ${retrievalResults.length} relevant chunks.`;
    }
    const generationMs = this.log.timeEnd('generation');

    const totalMs = this.log.timeEnd('query-total');

    const latency: LatencyMetrics = {
      embeddingMs,
      retrievalMs,
      generationMs,
      totalMs,
    };

    const debugInfo: DebugInfo | undefined = context.debug
      ? {
        retrievedChunks: retrievalResults.map((r) => r.chunk).filter(Boolean),
        scores: retrievalResults.map((r) => r.score),
        promptPreview: this.buildPromptPreview(queryText, retrievalResults),
        cacheHit: queryEmbedding.cached,
      }
      : undefined;

    this.log.info(`Query complete: ${totalMs}ms (embed: ${embeddingMs}ms, retrieve: ${retrievalMs}ms, gen: ${generationMs}ms)`);

    return {
      answer,
      results: retrievalResults,
      latency,
      debugInfo,
    };
  }

  /**
   * Rebuild the entire index from storage
   */
  async rebuildIndex(): Promise<{ chunks: number; embeddings: number }> {
    this.log.info('Rebuilding index from storage');

    // Clear in-memory state
    this.chunkEmbeddings.clear();

    // Reload from storage
    const chunks = await this.storage.getAllChunks();
    const embeddings = await this.storage.getAllEmbeddings();

    // Rebuild chunk embeddings map
    const embMap = new Map(embeddings.map((e) => [e.chunkId, e.vector]));
    this.chunkEmbeddings = embMap;

    // Rebuild keyword index
    this.keywordIndex = this.storage.getKeywordIndex();

    this.log.info(`Index rebuilt: ${chunks.length} chunks, ${embeddings.length} embeddings`);

    return {
      chunks: chunks.length,
      embeddings: embeddings.length,
    };
  }

  /**
   * Get statistics
   */
  async stats(): Promise<{
    documents: number;
    chunks: number;
    embeddings: number;
    cacheSize: number;
    keywordTerms: number;
  }> {
    const docs = await this.storage.getAllDocuments();
    const chunks = await this.storage.getAllChunks();
    const embeddings = await this.storage.getAllEmbeddings();

    return {
      documents: docs.length,
      chunks: chunks.length,
      embeddings: embeddings.length,
      cacheSize: this.embeddingsService.getCache().size(),
      keywordTerms: this.keywordIndex.size(),
    };
  }

  /**
   * Shutdown — flush all pending data
   */
  async shutdown(): Promise<void> {
    this.log.info('Shutting down pipeline');
    await this.storage.flush();
    await this.storage.close();
    this.embeddingsService.getCache().persist();
  }

  // Private helpers

  private async loadChunkEmbeddings(): Promise<void> {
    const embeddings = await this.storage.getAllEmbeddings();
    for (const emb of embeddings) {
      this.chunkEmbeddings.set(emb.chunkId, emb.vector);
    }
    this.log.info(`Loaded ${this.chunkEmbeddings.size} chunk embeddings`);
  }

  private buildPromptPreview(query: string, results: RetrievalResult[]): string {
    const preview = results.slice(0, 3).map((r, i) => {
      const content = r.chunk?.content?.substring(0, 100) || '[empty]';
      return `[${i + 1}] (${r.score.toFixed(3)}) ${content}...`;
    }).join('\n');

    return `Query: ${query}\n\nContext preview:\n${preview}`;
  }
}

export async function createPipeline(config: LightRagConfig): Promise<LightRagPipeline> {
  const pipeline = new LightRagPipeline(config);
  await pipeline.rebuildIndex();
  return pipeline;
}
