// Performance benchmarks

import { createPipeline, LightRagPipeline } from '../pipelines/pipeline.js';
import { DEFAULT_CONFIG, LightRagConfig } from '../config/types.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('benchmarks');

interface BenchmarkResult {
  name: string;
  iterations: number;
  avgMs: number;
  p50Ms: number;
  p95Ms: number;
  p99Ms: number;
  minMs: number;
  maxMs: number;
}

async function benchmark(name: string, fn: () => Promise<void>, iterations = 20): Promise<BenchmarkResult> {
  const latencies: number[] = [];

  for (let i = 0; i < iterations; i++) {
    const start = Date.now();
    await fn();
    latencies.push(Date.now() - start);
  }

  const sorted = [...latencies].sort((a, b) => a - b);
  const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length;

  return {
    name,
    iterations,
    avgMs: Math.round(avg * 100) / 100,
    p50Ms: sorted[Math.floor(iterations * 0.5)] ?? 0,
    p95Ms: sorted[Math.floor(iterations * 0.95)] ?? 0,
    p99Ms: sorted[Math.floor(iterations * 0.99)] ?? 0,
    minMs: sorted[0] ?? 0,
    maxMs: sorted[sorted.length - 1] ?? 0,
  };
}

function printResult(result: BenchmarkResult): void {
  console.log(`\n${result.name}:`);
  console.log(`  Avg:  ${result.avgMs}ms`);
  console.log(`  P50:  ${result.p50Ms}ms`);
  console.log(`  P95:  ${result.p95Ms}ms`);
  console.log(`  P99:  ${result.p99Ms}ms`);
  console.log(`  Min:  ${result.minMs}ms`);
  console.log(`  Max:  ${result.maxMs}ms`);
}

async function runBenchmarks(): Promise<void> {
  const config: LightRagConfig = {
    ...DEFAULT_CONFIG,
    storage: {
      ...DEFAULT_CONFIG.storage,
      dataDir: './data/benchmarks',
    },
  };

  const pipeline = await createPipeline(config);

  // Seed with test data
  for (let i = 0; i < 20; i++) {
    await pipeline.ingest(
      `Test document ${i}: This contains information about topic ${i} with details on subtopic ${i % 5}.`,
      { index: i },
    );
  }

  console.log('=== LightRAG Performance Benchmarks ===');
  console.log(`Documents: 20, Iterations: 20\n`);

  // Benchmark 1: Simple query
  const queryResult = await benchmark('query_simple', async () => {
    await pipeline.query('What is in the test documents?');
  });
  printResult(queryResult);

  // Benchmark 2: Ingestion
  const ingestResult = await benchmark('ingest_document', async () => {
    await pipeline.ingest('Benchmark test document with some content for timing.');
  });
  printResult(ingestResult);

  // Benchmark 3: Stats
  const statsResult = await benchmark('stats', async () => {
    await pipeline.stats();
  });
  printResult(statsResult);

  // Benchmark 4: Cache hit query
  await pipeline.query('Benchmark query'); // Prime cache
  const cacheHitResult = await benchmark('query_cache_hit', async () => {
    await pipeline.query('Benchmark query');
  });
  printResult(cacheHitResult);

  // Check targets
  console.log('\n=== Performance Targets ===');
  const targets = [
    { name: 'Query avg', target: 500, actual: queryResult.avgMs },
    { name: 'Query P95', target: 800, actual: queryResult.p95Ms },
    { name: 'Ingest avg', target: 200, actual: ingestResult.avgMs },
    { name: 'Cache hit', target: 50, actual: cacheHitResult.avgMs },
  ];

  for (const t of targets) {
    const status = t.actual < t.target ? '✅' : '⚠️';
    console.log(`${status} ${t.name}: ${t.actual}ms (target: <${t.target}ms)`);
  }

  await pipeline.shutdown();
}

runBenchmarks().catch((err) => {
  log.error(`Benchmarks failed: ${err}`);
  process.exit(1);
});
