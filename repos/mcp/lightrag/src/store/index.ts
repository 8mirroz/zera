// Keyword index for hybrid retrieval (BM25-like scoring)

import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { createLogger, Logger } from '../utils/logger.js';

export interface KeywordIndexData {
  postings: Record<string, Record<string, number>>; // term -> {docId -> count}
  docLengths: Record<string, number>; // docId -> token count
  numDocs: number;
  avgDocLength: number;
}

export class KeywordIndex {
  private log: Logger;
  private data: KeywordIndexData = {
    postings: {},
    docLengths: {},
    numDocs: 0,
    avgDocLength: 0,
  };
  private totalTokens = 0;

  constructor() {
    this.log = createLogger('keyword-index');
  }

  add(docId: string, content: string): void {
    const tokens = this.tokenize(content);
    this.data.docLengths[docId] = tokens.length;
    this.totalTokens += tokens.length;
    this.data.numDocs = Object.keys(this.data.docLengths).length;
    this.data.avgDocLength = this.totalTokens / this.data.numDocs;

    // Build postings
    const counts: Record<string, number> = {};
    for (const token of tokens) {
      counts[token] = (counts[token] || 0) + 1;
    }

    for (const [term, count] of Object.entries(counts)) {
      if (!this.data.postings[term]) {
        this.data.postings[term] = {};
      }
      this.data.postings[term]![docId] = count;
    }
  }

  remove(docId: string): void {
    const length = this.data.docLengths[docId];
    if (length === undefined) return;

    this.totalTokens -= length;
    delete this.data.docLengths[docId];
    this.data.numDocs = Object.keys(this.data.docLengths).length;
    this.data.avgDocLength = this.data.numDocs > 0 ? this.totalTokens / this.data.numDocs : 0;

    // Remove from postings
    for (const term of Object.keys(this.data.postings)) {
      delete this.data.postings[term]![docId];
      if (Object.keys(this.data.postings[term]!).length === 0) {
        delete this.data.postings[term];
      }
    }
  }

  search(query: string, maxResults: number = 20): Array<{ docId: string; score: number }> {
    const queryTokens = this.tokenize(query);
    const scores: Record<string, number> = {};

    for (const queryToken of queryTokens) {
      const posting = this.data.postings[queryToken];
      if (!posting) continue;

      for (const [docId, count] of Object.entries(posting)) {
        // Simple TF scoring with length normalization
        const docLength = this.data.docLengths[docId] || 1;
        const tf = count / docLength;
        scores[docId] = (scores[docId] || 0) + tf;
      }
    }

    // Sort by score and return top-k
    return Object.entries(scores)
      .map(([docId, score]) => ({ docId, score }))
      .sort((a, b) => b.score - a.score)
      .slice(0, maxResults);
  }

  persist(filePath: string): void {
    try {
      writeFileSync(filePath, JSON.stringify(this.data), 'utf-8');
      this.log.info(`Persisted keyword index: ${Object.keys(this.data.postings).length} terms`);
    } catch (err) {
      this.log.error(`Failed to persist keyword index: ${err}`);
    }
  }

  load(filePath: string): void {
    try {
      if (!existsSync(filePath)) return;
      const data = readFileSync(filePath, 'utf-8');
      this.data = JSON.parse(data);

      // Recalculate totals
      this.totalTokens = Object.values(this.data.docLengths).reduce((sum, len) => sum + len, 0);
      this.log.info(`Loaded keyword index: ${Object.keys(this.data.postings).length} terms, ${this.data.numDocs} docs`);
    } catch (err) {
      this.log.error(`Failed to load keyword index: ${err}`);
    }
  }

  private tokenize(text: string): string[] {
    return text
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean)
      .filter((token) => token.length > 2); // Skip very short tokens
  }

  getData(): KeywordIndexData {
    return this.data;
  }

  size(): number {
    return Object.keys(this.data.postings).length;
  }
}
