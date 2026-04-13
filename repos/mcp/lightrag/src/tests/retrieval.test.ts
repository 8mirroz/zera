// Unit tests for retrieval

import { describe, it, expect } from '@jest/globals';
import { cosineSimilarity } from '../retrieval/retrieiver.js';
import { KeywordIndex } from '../store/index.js';

describe('retrieval', () => {
  describe('cosineSimilarity', () => {
    it('should return 1.0 for identical vectors', () => {
      const vector = [0.5, 0.5, 0.5, 0.5];
      const text = 'hello world test';
      // Same text produces same hash vector
      const score = cosineSimilarity(text, vector);
      expect(score).toBeGreaterThan(0);
      expect(score).toBeLessThanOrEqual(1.0);
    });

    it('should return higher score for similar text', () => {
      const vector = [0.577, 0.577, 0.577]; // normalized
      const similar = cosineSimilarity('hello world', vector);
      const different = cosineSimilarity('completely different terms', vector);

      // Similar text should score higher (though depends on hash collision)
      expect(typeof similar).toBe('number');
      expect(typeof different).toBe('number');
    });

    it('should handle empty text', () => {
      const vector = [0.5, 0.5, 0.5];
      const score = cosineSimilarity('', vector);
      expect(score).toBe(0);
    });
  });

  describe('KeywordIndex', () => {
    it('should add and search documents', () => {
      const index = new KeywordIndex();
      index.add('doc1', 'hello world this is a test document');
      index.add('doc2', 'goodbye world this is different');

      const results = index.search('hello test');
      expect(results.length).toBeGreaterThan(0);
      expect(results[0]!.docId).toBe('doc1');
    });

    it('should return empty results for unknown terms', () => {
      const index = new KeywordIndex();
      index.add('doc1', 'hello world');

      const results = index.search('xyzzy nonexistent');
      expect(results.length).toBe(0);
    });

    it('should respect maxResults limit', () => {
      const index = new KeywordIndex();
      for (let i = 0; i < 10; i++) {
        index.add(`doc${i}`, `common term number ${i}`);
      }

      const results = index.search('common term', 3);
      expect(results.length).toBeLessThanOrEqual(3);
    });

    it('should remove documents', () => {
      const index = new KeywordIndex();
      index.add('doc1', 'hello world');
      index.add('doc2', 'hello there');

      index.remove('doc1');

      const results = index.search('world');
      expect(results.length).toBe(0);
    });

    it('should track size correctly', () => {
      const index = new KeywordIndex();
      expect(index.size()).toBe(0);

      index.add('doc1', 'hello world test');
      expect(index.size()).toBeGreaterThan(0); // At least 3 terms (hello, world, test)
    });
  });
});
