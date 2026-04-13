// Chunking engine — semantic + token-based with configurable overlap

import { ChunkingConfig } from '../config/types.js';
import { Chunk, Document } from '../types.js';
import { createLogger, Logger } from '../utils/logger.js';

// Sentence boundary patterns for semantic chunking
const SENTENCE_BOUNDARIES = [
  /[.!?]\s+/g,
  /[。！？]/g,
  /\n\s*\n/g,
  /[;；]\s+/g,
];

// Section headers for semantic boundaries
const SECTION_PATTERNS = [
  /^#{1,6}\s+.+$/gm,
  /^---+$/gm,
  /^\*{3}$/gm,
];

let logger: Logger | null = null;

function getLogger(): Logger {
  if (!logger) {
    logger = createLogger('chunking');
  }
  return logger;
}

/**
 * Estimate token count from text (rough: ~4 chars per token for English)
 * For Russian/mixed text this is approximate but fast
 */
export function estimateTokens(text: string): number {
  // More accurate estimation: split on whitespace and apply heuristic
  const words = text.split(/\s+/).filter(Boolean);
  let tokens = 0;
  for (const word of words) {
    // English words: ~1.3 tokens per word average
    // Longer words count more
    tokens += Math.ceil(word.length / 4);
  }
  return Math.max(1, tokens);
}

/**
 * Find semantic split points in text
 * Returns array of indices where semantic boundaries occur
 */
function findSemanticBoundaries(text: string): Set<number> {
  const boundaries = new Set<number>();

  // Find sentence boundaries
  for (const pattern of SENTENCE_BOUNDARIES) {
    let match: RegExpExecArray | null;
    pattern.lastIndex = 0;
    while ((match = pattern.exec(text)) !== null) {
      boundaries.add(match.index + match[0].length);
    }
  }

  // Find section headers
  for (const pattern of SECTION_PATTERNS) {
    let match: RegExpExecArray | null;
    pattern.lastIndex = 0;
    while ((match = pattern.exec(text)) !== null) {
      boundaries.add(match.index);
    }
  }

  return boundaries;
}

/**
 * Chunk a single document using token-based splitting with semantic awareness
 */
export function chunkDocument(
  document: Document,
  config: ChunkingConfig,
): Chunk[] {
  const log = getLogger();
  const startTime = Date.now();

  const { chunkSize, chunkOverlap, minChunkSize, semanticBoundaries } = config;

  // Pre-compute semantic boundaries
  const semanticPoints = semanticBoundaries
    ? findSemanticBoundaries(document.content)
    : new Set<number>();

  // Split text into tokens (word-level approximation)
  const words = document.content.split(/\s+/).filter(Boolean);
  if (words.length === 0) {
    return [];
  }

  // Build word-level token estimates
  const wordTokens: number[] = words.map((w) => Math.max(1, Math.ceil(w.length / 4)));

  const chunks: Chunk[] = [];
  let chunkIndex = 0;
  let wordStart = 0;

  while (wordStart < words.length) {
    // Find chunk end based on token budget
    let wordEnd = wordStart;
    let tokenCount = 0;

    while (wordEnd < words.length && tokenCount < chunkSize) {
      tokenCount += wordTokens[wordEnd]!;

      // Check if we're at a semantic boundary near the target chunk size
      if (tokenCount >= chunkSize * 0.8 && tokenCount <= chunkSize) {
        // Calculate approximate character position
        const charPos = words.slice(wordStart, wordEnd + 1).join(' ').length;
        const absPos = getCharPosition(words, wordStart, wordEnd + 1);

        if (semanticPoints.has(absPos) || isNearBoundary(semanticPoints, absPos, 50)) {
          wordEnd++;
          break;
        }
      }

      wordEnd++;
    }

    // Ensure we don't exceed max
    wordEnd = Math.min(wordEnd, words.length);

    // Extract chunk text
    const chunkWords = words.slice(wordStart, wordEnd);
    const content = chunkWords.join(' ');
    const actualTokens = estimateTokens(content);

    // Skip too-small chunks (merge with previous if possible)
    if (actualTokens < minChunkSize && chunks.length > 0) {
      const prev = chunks[chunks.length - 1]!;
      prev.content += ' ' + content;
      prev.tokenCount = estimateTokens(prev.content);
      wordStart = wordEnd;
      continue;
    }

    // Create chunk
    const chunk: Chunk = {
      id: `${document.id}_chunk_${chunkIndex}`,
      documentId: document.id,
      content,
      index: chunkIndex,
      tokenCount: actualTokens,
      metadata: {
        ...document.metadata,
        chunkIndex,
        wordStart,
        wordEnd,
      },
    };

    chunks.push(chunk);
    chunkIndex++;

    // Move start with overlap
    if (chunkOverlap > 0 && wordEnd < words.length) {
      // Backtrack for overlap
      let overlapTokens = 0;
      let overlapStart = wordEnd - 1;
      while (overlapStart > wordStart && overlapTokens < chunkOverlap) {
        overlapTokens += wordTokens[overlapStart]!;
        overlapStart--;
      }
      wordStart = overlapStart + 1;
    } else {
      wordStart = wordEnd;
    }
  }

  const duration = Date.now() - startTime;
  log.debug(`Chunked document ${document.id}: ${chunks.length} chunks in ${duration}ms`, {
    totalTokens: words.reduce((a: number, b: string) => a + b.length, 0),
    chunkSizes: chunks.map((c) => c.tokenCount),
  });

  return chunks;
}

/**
 * Get approximate character position in original text
 */
function getCharPosition(words: string[], start: number, end: number): number {
  let pos = 0;
  for (let i = 0; i < start; i++) {
    pos += words[i]!.length + 1; // +1 for space
  }
  return pos;
}

/**
 * Check if position is near a semantic boundary
 */
function isNearBoundary(boundaries: Set<number>, position: number, tolerance: number): boolean {
  for (const boundary of boundaries) {
    if (Math.abs(boundary - position) <= tolerance) {
      return true;
    }
  }
  return false;
}

/**
 * Chunk multiple documents
 */
export function chunkDocuments(documents: Document[], config: ChunkingConfig): Chunk[] {
  const log = getLogger();
  log.info(`Chunking ${documents.length} documents`);

  const allChunks: Chunk[] = [];
  for (const doc of documents) {
    const chunks = chunkDocument(doc, config);
    allChunks.push(...chunks);
  }

  log.info(`Total chunks: ${allChunks.length}`);
  return allChunks;
}

/**
 * Split text by semantic boundaries without token counting (fast path)
 */
export function semanticSplit(text: string, maxChunkChars: number = 2000): string[] {
  const chunks: string[] = [];
  let remaining = text;

  while (remaining.length > 0) {
    if (remaining.length <= maxChunkChars) {
      chunks.push(remaining);
      break;
    }

    // Find best split point near the middle
    const midpoint = Math.floor(maxChunkChars * 0.8);
    let splitPoint = -1;

    // Try to find sentence boundary
    for (let i = midpoint; i < Math.min(midpoint + 200, remaining.length); i++) {
      const char = remaining[i];
      if (char === '.' || char === '!' || char === '?' || char === '\n') {
        splitPoint = i + 1;
        break;
      }
    }

    // Fallback: split at word boundary
    if (splitPoint === -1 || splitPoint >= remaining.length) {
      splitPoint = Math.min(maxChunkChars, remaining.length);
      // Don't split in middle of word
      while (splitPoint > 0 && remaining[splitPoint] !== ' ' && remaining[splitPoint] !== '\n') {
        splitPoint--;
      }
      if (splitPoint <= 0) splitPoint = Math.min(maxChunkChars, remaining.length);
    }

    chunks.push(remaining.slice(0, splitPoint).trim());
    remaining = remaining.slice(splitPoint).trim();
  }

  return chunks;
}
