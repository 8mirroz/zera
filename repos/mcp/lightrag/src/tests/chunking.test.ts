// Unit tests for chunking engine

import { describe, it, expect } from '@jest/globals';
import { chunkDocument, estimateTokens, semanticSplit } from '../chunking/chunker.js';
import { Document } from '../types.js';
import { DEFAULT_CONFIG } from '../config/types.js';

describe('chunking', () => {
  const createDoc = (content: string): Document => ({
    id: 'test-doc-1',
    content,
    metadata: {},
    createdAt: Date.now(),
    updatedAt: Date.now(),
  });

  describe('estimateTokens', () => {
    it('should estimate tokens for simple text', () => {
      const text = 'hello world';
      const tokens = estimateTokens(text);
      expect(tokens).toBeGreaterThan(0);
      expect(tokens).toBeLessThan(10);
    });

    it('should handle empty text', () => {
      expect(estimateTokens('')).toBe(1);
      expect(estimateTokens('   ')).toBe(1);
    });

    it('should scale with text length', () => {
      const short = estimateTokens('hello');
      const long = estimateTokens('hello world this is a longer text with more words');
      expect(long).toBeGreaterThan(short);
    });
  });

  describe('chunkDocument', () => {
    it('should chunk short text into single chunk', () => {
      const doc = createDoc('This is a short text that fits in one chunk.');
      const chunks = chunkDocument(doc, {
        ...DEFAULT_CONFIG.chunking,
        chunkSize: 512,
        chunkOverlap: 0,
      });

      expect(chunks.length).toBe(1);
      expect(chunks[0]!.content).toContain('short text');
    });

    it('should split long text into multiple chunks', () => {
      const content = Array(200).fill('word').join(' ');
      const doc = createDoc(content);
      const chunks = chunkDocument(doc, {
        ...DEFAULT_CONFIG.chunking,
        chunkSize: 64,
        chunkOverlap: 8,
        minChunkSize: 16,
        semanticBoundaries: false,
      });

      expect(chunks.length).toBeGreaterThan(1);
    });

    it('should preserve document metadata in chunks', () => {
      const doc = createDoc('Test content');
      doc.metadata = { source: 'test', tag: 'unit' };
      const chunks = chunkDocument(doc, DEFAULT_CONFIG.chunking);

      expect(chunks[0]!.metadata.source).toBe('test');
      expect(chunks[0]!.metadata.tag).toBe('unit');
    });

    it('should create sequential chunk indices', () => {
      const content = Array(300).fill('token').join(' ');
      const doc = createDoc(content);
      const chunks = chunkDocument(doc, {
        ...DEFAULT_CONFIG.chunking,
        chunkSize: 48,
        chunkOverlap: 0,
        minChunkSize: 16,
        semanticBoundaries: false,
      });

      for (let i = 0; i < chunks.length; i++) {
        expect(chunks[i]!.index).toBe(i);
      }
    });
  });

  describe('semanticSplit', () => {
    it('should split text at sentence boundaries', () => {
      const text = 'First sentence. Second sentence. Third sentence.';
      const chunks = semanticSplit(text, 20);

      expect(chunks.length).toBeGreaterThan(1);
      expect(chunks[0]!.endsWith('.')).toBe(true);
    });

    it('should handle text shorter than max chunk', () => {
      const text = 'Short text.';
      const chunks = semanticSplit(text, 100);

      expect(chunks.length).toBe(1);
      expect(chunks[0]).toBe('Short text.');
    });

    it('should not split in middle of words', () => {
      const text = 'ThisIsAVeryLongWord ' + Array(50).fill('extra').join(' ');
      const chunks = semanticSplit(text, 15);

      for (const chunk of chunks) {
        expect(chunk).not.toMatch(/^[a-zA-Z]+$/); // Shouldn't be partial word
      }
    });
  });
});
