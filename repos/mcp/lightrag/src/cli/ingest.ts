// CLI ingest command

import { readFileSync, existsSync } from 'node:fs';
import { basename } from 'node:path';
import { createPipeline } from '../pipelines/pipeline.js';
import { DEFAULT_CONFIG } from '../config/types.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('cli-ingest');

interface IngestArgs {
  file?: string;
  text?: string;
  metadata?: string;
  debug?: boolean;
}

export async function ingestCommand(args: IngestArgs): Promise<void> {
  let content = '';
  let source = 'cli';

  if (args.file) {
    if (!existsSync(args.file)) {
      log.error(`File not found: ${args.file}`);
      process.exit(1);
    }
    content = readFileSync(args.file, 'utf-8');
    source = basename(args.file);
    log.info(`Read ${content.length} chars from ${args.file}`);
  } else if (args.text) {
    content = args.text;
    log.info(`Using provided text: ${content.length} chars`);
  } else {
    // Read from stdin
    log.info('Reading from stdin...');
    const chunks: Buffer[] = [];
    for await (const chunk of process.stdin) {
      chunks.push(chunk);
    }
    content = Buffer.concat(chunks).toString('utf-8');
  }

  if (!content.trim()) {
    log.error('No content to ingest');
    process.exit(1);
  }

  const metadata: Record<string, unknown> = {
    source,
    ingestedAt: new Date().toISOString(),
  };

  if (args.metadata) {
    try {
      Object.assign(metadata, JSON.parse(args.metadata));
    } catch {
      log.error(`Invalid metadata JSON: ${args.metadata}`);
      process.exit(1);
    }
  }

  const config = {
    ...DEFAULT_CONFIG,
    debug: args.debug ?? false,
  };

  const pipeline = await createPipeline(config);

  try {
    const result = await pipeline.ingest(content, metadata);
    console.log(JSON.stringify({
      success: true,
      documentId: result.documentId,
      chunksCreated: result.chunksCreated,
      embeddingsGenerated: result.embeddingsGenerated,
      latency: `${result.latency}ms`,
    }, null, 2));
  } catch (err) {
    log.error(`Ingestion failed: ${err}`);
    console.error(JSON.stringify({ success: false, error: String(err) }, null, 2));
    process.exit(1);
  } finally {
    await pipeline.shutdown();
  }
}
