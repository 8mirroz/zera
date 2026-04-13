// CLI query command

import { createPipeline } from '../pipelines/pipeline.js';
import { DEFAULT_CONFIG } from '../config/types.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('cli-query');

interface QueryArgs {
  query: string;
  topK?: number;
  debug?: boolean;
}

export async function queryCommand(args: QueryArgs): Promise<void> {
  if (!args.query) {
    log.error('No query provided');
    process.exit(1);
  }

  const config = {
    ...DEFAULT_CONFIG,
    debug: args.debug ?? false,
    retrieval: {
      ...DEFAULT_CONFIG.retrieval,
      topK: args.topK ?? DEFAULT_CONFIG.retrieval.topK,
    },
  };

  const pipeline = await createPipeline(config);

  try {
    const response = await pipeline.query(args.query, { debug: config.debug });

    // Output answer
    console.log('\n=== Answer ===\n');
    console.log(response.answer);

    // Output latency
    console.log('\n=== Latency ===\n');
    console.log(`  Embedding:  ${response.latency.embeddingMs}ms`);
    console.log(`  Retrieval:  ${response.latency.retrievalMs}ms`);
    console.log(`  Generation: ${response.latency.generationMs}ms`);
    console.log(`  Total:      ${response.latency.totalMs}ms`);
    console.log(`  Cache hit:  ${response.debugInfo?.cacheHit ?? false}`);

    // Output debug info if enabled
    if (config.debug && response.debugInfo) {
      console.log('\n=== Debug: Retrieved Chunks ===\n');
      for (let i = 0; i < response.debugInfo.retrievedChunks.length; i++) {
        const chunk = response.debugInfo.retrievedChunks[i]!;
        const score = response.debugInfo.scores[i]!;
        console.log(`[${i + 1}] Score: ${score.toFixed(4)} | ${chunk.tokenCount} tokens`);
        console.log(`    Doc: ${chunk.documentId} | Chunk: ${chunk.index}`);
        console.log(`    Preview: ${chunk.content.substring(0, 150)}...`);
        console.log();
      }
    }

    // Output stats
    const stats = await pipeline.stats();
    console.log('\n=== Index Stats ===\n');
    console.log(`  Documents: ${stats.documents}`);
    console.log(`  Chunks:    ${stats.chunks}`);
    console.log(`  Embeddings: ${stats.embeddings}`);
    console.log(`  Cache:     ${stats.cacheSize} entries`);
    console.log(`  Keywords:  ${stats.keywordTerms} terms`);
  } catch (err) {
    log.error(`Query failed: ${err}`);
    console.error(JSON.stringify({ success: false, error: String(err) }, null, 2));
    process.exit(1);
  } finally {
    await pipeline.shutdown();
  }
}
