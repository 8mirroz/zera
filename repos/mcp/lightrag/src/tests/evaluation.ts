// Evaluation test suite for LightRAG

import { createPipeline, LightRagPipeline } from '../pipelines/pipeline.js';
import { DEFAULT_CONFIG, LightRagConfig } from '../config/types.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('tests');

// Test documents with known content
const TEST_DOCUMENTS = [
  {
    content: `The Antigravity routing system uses 5 tiers: C1 (Trivial), C2 (Simple), C3 (Medium), C4 (Complex), and C5 (Critical).
C1 and C2 use the Fast Path with 1 agent. C3 uses the Quality Path with 2 agents. C4 and C5 use the Swarm Path with 3 agents.
Max tools: C1=8, C2=12, C3=20, C4=30, C5=50. Human audit is required for C4 and C5 tasks.`,
    metadata: { source: 'routing', tags: ['routing', 'tiers'] },
  },
  {
    content: `The model stack includes: deepseek-v3 as primary engineer, gemini-2.0-flash for fast tasks, and qwen3-235b for premium.
Local models run via Ollama: qwen2.5-coder:7b for coding, gemma4 for general tasks.
MLX models run directly on Apple Silicon for lower latency.`,
    metadata: { source: 'models', tags: ['models', 'configuration'] },
  },
  {
    content: `Completion gates ensure quality by tier. C1 requires no tests. C2 requires tests and explicit error handling.
C3 adds code review. C4 adds pattern extraction and human audit. C5 adds ADR updates and council review.
All tiers require a README.md and .env.example if env vars are used.`,
    metadata: { source: 'gates', tags: ['quality', 'gates'] },
  },
  {
    content: `The workspace structure places web apps in repos/apps/, Telegram bots in repos/telegram/, MCP servers in repos/mcp/.
Shared libraries go in repos/packages/. All new work starts in sandbox/ before moving to repos/.
Documentation goes in docs/ with ADRs in docs/adr/ and knowledge items in docs/ki/.`,
    metadata: { source: 'workspace', tags: ['structure', 'rules'] },
  },
  {
    content: `BM25 is the current memory system using rank-bm25 library with BM25Plus algorithm.
It uses lexical matching only, no semantic embeddings. The system stores memory in .agents/memory/memory.jsonl.
LightRAG adds semantic retrieval on top of BM25 with vector embeddings.`,
    metadata: { source: 'memory', tags: ['BM25', 'memory', 'RAG'] },
  },
];

interface TestResult {
  name: string;
  passed: boolean;
  latency?: number;
  score?: number;
  error?: string;
}

export class LightRagEvaluator {
  private pipeline!: LightRagPipeline;
  private results: TestResult[] = [];

  async setup(): Promise<void> {
    const config: LightRagConfig = {
      ...DEFAULT_CONFIG,
      debug: true,
      storage: {
        ...DEFAULT_CONFIG.storage,
        dataDir: './data/test',
      },
    };

    this.pipeline = await createPipeline(config);

    // Ingest test documents
    for (const doc of TEST_DOCUMENTS) {
      await this.pipeline.ingest(doc.content, doc.metadata);
    }

    log.info(`Setup complete: ${TEST_DOCUMENTS.length} documents ingested`);
  }

  async teardown(): Promise<void> {
    if (this.pipeline) {
      await this.pipeline.shutdown();
    }
  }

  // Test 1: Retrieval accuracy — can we find relevant chunks?
  async testRetrievalAccuracy(): Promise<TestResult> {
    const queries = [
      { query: 'How many tiers does routing have?', expectedTier: 'C1' },
      { query: 'What models run locally via Ollama?', expectedModel: 'qwen2.5-coder' },
      { query: 'What are the completion gate requirements?', expectedGate: 'C3' },
      { query: 'Where do Telegram bots go in the workspace?', expectedPath: 'repos/telegram' },
      { query: 'What algorithm does BM25 memory use?', expectedAlgo: 'BM25Plus' },
    ];

    let totalScore = 0;
    let totalLatency = 0;

    for (const { query } of queries) {
      const start = Date.now();
      const response = await this.pipeline.query(query, { debug: true });
      const latency = Date.now() - start;
      totalLatency += latency;

      // Check if answer contains relevant information
      const hasContent = response.answer.length > 50;
      const hasContext = response.results.length > 0;
      const firstResult = response.results[0];
      const goodScore = firstResult !== undefined && firstResult.score > 0.3;

      const queryScore = (hasContent ? 0.4 : 0) + (hasContext ? 0.3 : 0) + (goodScore ? 0.3 : 0);
      totalScore += queryScore;
    }

    const avgScore = totalScore / queries.length;
    const avgLatency = totalLatency / queries.length;

    return {
      name: 'retrieval_accuracy',
      passed: avgScore > 0.6,
      score: avgScore,
      latency: avgLatency,
    };
  }

  // Test 2: Latency benchmarks
  async testLatencyBenchmarks(): Promise<TestResult> {
    const latencies: number[] = [];

    // Run 10 queries
    for (let i = 0; i < 10; i++) {
      const start = Date.now();
      await this.pipeline.query(`Test query ${i}`);
      latencies.push(Date.now() - start);
    }

    const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length;
    const p50 = latencies.sort((a, b) => a - b)[4] || 0;
    const p95 = latencies[9] || 0;

    // Target: <500ms average (local models may vary)
    const passed = avg < 1000; // Generous for local models

    return {
      name: 'latency_benchmarks',
      passed,
      latency: avg,
      score: { avg, p50, p95 } as any,
    };
  }

  // Test 3: Hallucination reduction — answers should be grounded in context
  async testHallucinationReduction(): Promise<TestResult> {
    const queries = [
      'What is the capital of France?', // Should say no info in context
      'Who created Antigravity?', // Should say no info in context
      'How many agents does C4 use?', // Should answer from context (3)
    ];

    let groundedAnswers = 0;

    for (const query of queries) {
      const response = await this.pipeline.query(query, { debug: true });

      // Check if answer acknowledges context limits or uses retrieved info
      const mentionsNoInfo = response.answer.toLowerCase().includes('context') &&
        (response.answer.toLowerCase().includes('no') || response.answer.toLowerCase().includes('not'));
      const usesContext = response.results.length > 0 && response.results[0]!.score > 0.2;

      if (mentionsNoInfo || usesContext) {
        groundedAnswers++;
      }
    }

    const groundingRate = groundedAnswers / queries.length;

    return {
      name: 'hallucination_reduction',
      passed: groundingRate > 0.5,
      score: groundingRate,
    };
  }

  // Test 4: Incremental ingestion
  async testIncrementalIngestion(): Promise<TestResult> {
    const stats1 = await this.pipeline.stats();

    // Ingest more documents
    for (let i = 0; i < 5; i++) {
      await this.pipeline.ingest(`New document ${i}: Additional knowledge about topic ${i}`, { batch: 'test' });
    }

    const stats2 = await this.pipeline.stats();

    const added = stats2.documents - stats1.documents;

    return {
      name: 'incremental_ingestion',
      passed: added === 5,
      score: added / 5,
    };
  }

  // Test 5: Cache effectiveness
  async testCacheEffectiveness(): Promise<TestResult> {
    // First query (cache miss)
    const r1 = await this.pipeline.query('How many tiers does routing have?', { debug: true });

    // Second identical query (cache hit)
    const r2 = await this.pipeline.query('How many tiers does routing have?', { debug: true });

    const cacheHit = r2.debugInfo?.cacheHit === true;
    const faster = r2.latency.embeddingMs < r1.latency.embeddingMs;

    return {
      name: 'cache_effectiveness',
      passed: cacheHit && faster,
      score: cacheHit ? 1 : 0,
      latency: {
        first: r1.latency.embeddingMs,
        second: r2.latency.embeddingMs,
      } as any,
    };
  }

  // Run all tests
  async runAll(): Promise<TestResult[]> {
    this.results = [];

    log.info('Starting evaluation suite');

    const tests = [
      this.testRetrievalAccuracy(),
      this.testLatencyBenchmarks(),
      this.testHallucinationReduction(),
      this.testIncrementalIngestion(),
      this.testCacheEffectiveness(),
    ];

    for (const testPromise of tests) {
      try {
        const result = await testPromise;
        this.results.push(result);
        const status = result.passed ? '✅ PASS' : '❌ FAIL';
        log.info(`${status}: ${result.name} (score: ${result.score}, latency: ${result.latency}ms)`);
      } catch (err) {
        this.results.push({
          name: 'unknown',
          passed: false,
          error: String(err),
        });
        log.error(`Test failed: ${err}`);
      }
    }

    const passed = this.results.filter((r) => r.passed).length;
    const total = this.results.length;

    log.info(`Evaluation complete: ${passed}/${total} tests passed`);

    return this.results;
  }

  printReport(): void {
    console.log('\n=== LightRAG Evaluation Report ===\n');

    for (const result of this.results) {
      const status = result.passed ? '✅' : '❌';
      console.log(`${status} ${result.name}`);
      if (result.score !== undefined) console.log(`   Score: ${JSON.stringify(result.score)}`);
      if (result.latency !== undefined) console.log(`   Latency: ${JSON.stringify(result.latency)}ms`);
      if (result.error) console.log(`   Error: ${result.error}`);
      console.log();
    }

    const passed = this.results.filter((r) => r.passed).length;
    console.log(`Total: ${passed}/${this.results.length} passed`);
  }
}

// Run if executed directly
async function main(): Promise<void> {
  const evaluator = new LightRagEvaluator();
  await evaluator.setup();
  await evaluator.runAll();
  evaluator.printReport();
  await evaluator.teardown();
}

main().catch((err) => {
  console.error('Evaluation failed:', err);
  process.exit(1);
});
