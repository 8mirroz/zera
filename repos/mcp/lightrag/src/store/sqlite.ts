// SQLite storage adapter — optional lightweight backend

import { existsSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { StorageConfig } from '../config/types.js';
import { Document, Chunk, Embedding } from '../types.js';
import { createLogger, Logger } from '../utils/logger.js';
import { KeywordIndex } from './index.js';
import { StorageAdapter } from './jsonl.js';

// Dynamic import for better-sqlite3 (optional dependency)
let Database: any;

export class SqliteStorage implements StorageAdapter {
  private log: Logger;
  private db: any;
  private keywordIndex: KeywordIndex;
  private ready = false;

  constructor(private config: StorageConfig) {
    this.log = createLogger('storage-sqlite');
    this.keywordIndex = new KeywordIndex();

    if (!existsSync(config.dataDir)) {
      mkdirSync(config.dataDir, { recursive: true });
    }
  }

  private async init(): Promise<void> {
    if (this.ready) return;

    try {
      // Lazy load better-sqlite3
      if (!Database) {
        const sqlite = await import('better-sqlite3');
        Database = sqlite.default;
      }

      const dbPath = join(this.config.dataDir, 'lightrag.sqlite');
      this.db = new Database(dbPath);

      // Create tables
      this.db.exec(`
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY,
          content TEXT NOT NULL,
          metadata TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          updated_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chunks (
          id TEXT PRIMARY KEY,
          document_id TEXT NOT NULL,
          content TEXT NOT NULL,
          chunk_index INTEGER NOT NULL,
          token_count INTEGER NOT NULL,
          metadata TEXT NOT NULL,
          FOREIGN KEY (document_id) REFERENCES documents(id)
        );

        CREATE TABLE IF NOT EXISTS embeddings (
          chunk_id TEXT PRIMARY KEY,
          vector TEXT NOT NULL,
          model TEXT NOT NULL,
          dimensions INTEGER NOT NULL,
          FOREIGN KEY (chunk_id) REFERENCES chunks(id)
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
      `);

      this.db.pragma('journal_mode = WAL');
      this.db.pragma('synchronous = NORMAL');
      this.db.pragma('cache_size = -2000'); // 2MB cache

      this.ready = true;
      this.log.info('SQLite storage initialized');
    } catch (err) {
      this.log.warn(`SQLite not available, falling back to JSONL: ${err}`);
      throw err;
    }
  }

  async saveDocument(doc: Document): Promise<void> {
    await this.init();
    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO documents (id, content, metadata, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?)
    `);
    stmt.run(doc.id, doc.content, JSON.stringify(doc.metadata), doc.createdAt, doc.updatedAt);
  }

  async saveChunk(chunk: Chunk): Promise<void> {
    await this.init();
    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO chunks (id, document_id, content, chunk_index, token_count, metadata)
      VALUES (?, ?, ?, ?, ?, ?)
    `);
    stmt.run(chunk.id, chunk.documentId, chunk.content, chunk.index, chunk.tokenCount, JSON.stringify(chunk.metadata));
    this.keywordIndex.add(chunk.id, chunk.content);
  }

  async saveEmbedding(embedding: Embedding): Promise<void> {
    await this.init();
    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO embeddings (chunk_id, vector, model, dimensions)
      VALUES (?, ?, ?, ?)
    `);
    stmt.run(embedding.chunkId, JSON.stringify(embedding.vector), embedding.model, embedding.dimensions);
  }

  async getDocument(id: string): Promise<Document | undefined> {
    await this.init();
    const row = this.db.prepare('SELECT * FROM documents WHERE id = ?').get(id);
    if (!row) return undefined;

    return {
      id: row.id,
      content: row.content,
      metadata: JSON.parse(row.metadata),
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }

  async getAllDocuments(): Promise<Document[]> {
    await this.init();
    return this.db.prepare('SELECT * FROM documents').all().map((row: any) => ({
      id: row.id,
      content: row.content,
      metadata: JSON.parse(row.metadata),
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    }));
  }

  async getAllChunks(): Promise<Chunk[]> {
    await this.init();
    return this.db.prepare('SELECT * FROM chunks').all().map((row: any) => ({
      id: row.id,
      documentId: row.document_id,
      content: row.content,
      index: row.chunk_index,
      tokenCount: row.token_count,
      metadata: JSON.parse(row.metadata),
    }));
  }

  async getAllEmbeddings(): Promise<Embedding[]> {
    await this.init();
    return this.db.prepare('SELECT * FROM embeddings').all().map((row: any) => ({
      chunkId: row.chunk_id,
      vector: JSON.parse(row.vector),
      model: row.model,
      dimensions: row.dimensions,
    }));
  }

  async getChunksForDocument(documentId: string): Promise<Chunk[]> {
    await this.init();
    return this.db.prepare('SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index').all(documentId).map((row: any) => ({
      id: row.id,
      documentId: row.document_id,
      content: row.content,
      index: row.chunk_index,
      tokenCount: row.token_count,
      metadata: JSON.parse(row.metadata),
    }));
  }

  async getEmbeddingsForChunk(chunkId: string): Promise<Embedding[]> {
    await this.init();
    const row = this.db.prepare('SELECT * FROM embeddings WHERE chunk_id = ?').get(chunkId);
    if (!row) return [];

    return [{
      chunkId: row.chunk_id,
      vector: JSON.parse(row.vector),
      model: row.model,
      dimensions: row.dimensions,
    }];
  }

  async flush(): Promise<void> {
    await this.init();
    this.db.exec('PRAGMA wal_checkpoint(TRUNCATE)');
  }

  async close(): Promise<void> {
    if (this.db) {
      await this.flush();
      this.db.close();
      this.keywordIndex.persist(join(this.config.dataDir, 'keyword_index.json'));
    }
  }

  getKeywordIndex(): KeywordIndex {
    return this.keywordIndex;
  }
}
