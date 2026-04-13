// Storage layer — JSONL + in-memory index

import { existsSync, mkdirSync, appendFileSync, readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { StorageConfig } from '../config/types.js';
import { Document, Chunk, Embedding } from '../types.js';
import { createLogger, Logger } from '../utils/logger.js';
import { KeywordIndex } from './index.js';

export interface StorageAdapter {
  saveDocument(doc: Document): Promise<void>;
  saveChunk(chunk: Chunk): Promise<void>;
  saveEmbedding(embedding: Embedding): Promise<void>;
  getDocument(id: string): Promise<Document | undefined>;
  getAllDocuments(): Promise<Document[]>;
  getAllChunks(): Promise<Chunk[]>;
  getAllEmbeddings(): Promise<Embedding[]>;
  getChunksForDocument(documentId: string): Promise<Chunk[]>;
  getEmbeddingsForChunk(chunkId: string): Promise<Embedding[]>;
  flush(): Promise<void>;
  close(): Promise<void>;
  getKeywordIndex(): KeywordIndex;
}

export class JsonlStorage implements StorageAdapter {
  private log: Logger;
  private documents: Map<string, Document>;
  private chunks: Map<string, Chunk>;
  private embeddings: Map<string, Embedding>;
  private keywordIndex: KeywordIndex;
  private pendingDocs: Document[] = [];
  private pendingChunks: Chunk[] = [];
  private pendingEmbeddings: Embedding[] = [];
  private docFile: string;
  private chunkFile: string;
  private embeddingFile: string;
  private ingestCount = 0;

  constructor(private config: StorageConfig) {
    this.log = createLogger('storage');
    this.documents = new Map();
    this.chunks = new Map();
    this.embeddings = new Map();
    this.keywordIndex = new KeywordIndex();

    this.docFile = join(config.dataDir, 'documents.jsonl');
    this.chunkFile = join(config.dataDir, 'chunks.jsonl');
    this.embeddingFile = join(config.dataDir, 'embeddings.jsonl');

    // Ensure data directory exists
    if (!existsSync(config.dataDir)) {
      mkdirSync(config.dataDir, { recursive: true });
    }

    this.load();
  }

  async saveDocument(doc: Document): Promise<void> {
    this.documents.set(doc.id, doc);
    this.pendingDocs.push(doc);
    this.ingestCount++;

    if (this.ingestCount >= this.config.flushThreshold) {
      await this.flush();
    }
  }

  async saveChunk(chunk: Chunk): Promise<void> {
    this.chunks.set(chunk.id, chunk);
    this.pendingChunks.push(chunk);

    // Update keyword index
    this.keywordIndex.add(chunk.id, chunk.content);
  }

  async saveEmbedding(embedding: Embedding): Promise<void> {
    this.embeddings.set(embedding.chunkId, embedding);
    this.pendingEmbeddings.push(embedding);
  }

  async getDocument(id: string): Promise<Document | undefined> {
    return this.documents.get(id);
  }

  async getAllDocuments(): Promise<Document[]> {
    return Array.from(this.documents.values());
  }

  async getAllChunks(): Promise<Chunk[]> {
    return Array.from(this.chunks.values());
  }

  async getAllEmbeddings(): Promise<Embedding[]> {
    return Array.from(this.embeddings.values());
  }

  async getChunksForDocument(documentId: string): Promise<Chunk[]> {
    return Array.from(this.chunks.values()).filter((c) => c.documentId === documentId);
  }

  async getEmbeddingsForChunk(chunkId: string): Promise<Embedding[]> {
    const emb = this.embeddings.get(chunkId);
    return emb ? [emb] : [];
  }

  async flush(): Promise<void> {
    try {
      if (this.pendingDocs.length > 0) {
        for (const doc of this.pendingDocs) {
          appendFileSync(this.docFile, JSON.stringify(doc) + '\n');
        }
        this.log.debug(`Flushed ${this.pendingDocs.length} documents`);
        this.pendingDocs = [];
      }

      if (this.pendingChunks.length > 0) {
        for (const chunk of this.pendingChunks) {
          appendFileSync(this.chunkFile, JSON.stringify(chunk) + '\n');
        }
        this.log.debug(`Flushed ${this.pendingChunks.length} chunks`);
        this.pendingChunks = [];
      }

      if (this.pendingEmbeddings.length > 0) {
        for (const emb of this.pendingEmbeddings) {
          appendFileSync(this.embeddingFile, JSON.stringify(emb) + '\n');
        }
        this.log.debug(`Flushed ${this.pendingEmbeddings.length} embeddings`);
        this.pendingEmbeddings = [];
      }

      this.ingestCount = 0;
    } catch (err) {
      this.log.error(`Failed to flush storage: ${err}`);
      throw err;
    }
  }

  async close(): Promise<void> {
    await this.flush();
    this.keywordIndex.persist(join(this.config.dataDir, 'keyword_index.json'));
  }

  getKeywordIndex(): KeywordIndex {
    return this.keywordIndex;
  }

  private load(): void {
    this.log.info('Loading data from JSONL files');

    if (existsSync(this.docFile)) {
      const lines = readFileSync(this.docFile, 'utf-8').trim().split('\n').filter(Boolean);
      for (const line of lines) {
        try {
          const doc: Document = JSON.parse(line);
          this.documents.set(doc.id, doc);
        } catch {
          this.log.warn(`Failed to parse document line`);
        }
      }
      this.log.info(`Loaded ${this.documents.size} documents`);
    }

    if (existsSync(this.chunkFile)) {
      const lines = readFileSync(this.chunkFile, 'utf-8').trim().split('\n').filter(Boolean);
      for (const line of lines) {
        try {
          const chunk: Chunk = JSON.parse(line);
          this.chunks.set(chunk.id, chunk);
          this.keywordIndex.add(chunk.id, chunk.content);
        } catch {
          this.log.warn(`Failed to parse chunk line`);
        }
      }
      this.log.info(`Loaded ${this.chunks.size} chunks`);
    }

    if (existsSync(this.embeddingFile)) {
      const lines = readFileSync(this.embeddingFile, 'utf-8').trim().split('\n').filter(Boolean);
      for (const line of lines) {
        try {
          const emb: Embedding = JSON.parse(line);
          this.embeddings.set(emb.chunkId, emb);
        } catch {
          this.log.warn(`Failed to parse embedding line`);
        }
      }
      this.log.info(`Loaded ${this.embeddings.size} embeddings`);
    }

    // Load keyword index
    const indexFile = join(this.config.dataDir, 'keyword_index.json');
    if (existsSync(indexFile)) {
      this.keywordIndex.load(indexFile);
    }
  }
}
