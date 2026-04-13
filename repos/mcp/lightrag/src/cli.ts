// Main CLI entry point

import { createLogger } from './utils/logger.js';
import { ingestCommand } from './cli/ingest.js';
import { queryCommand } from './cli/query.js';

const log = createLogger('cli');

function printHelp(): void {
  console.log(`
LightRAG CLI — Lightweight RAG for Antigravity Core

Usage:
  lightrag <command> [options]

Commands:
  ingest    Ingest a document into the knowledge base
  query     Query the knowledge base
  stats     Show index statistics
  rebuild   Rebuild the index from storage
  help      Show this help message

Ingest Options:
  --file <path>      File to ingest
  --text <text>      Text to ingest
  --metadata <json>  JSON metadata
  --debug            Enable debug output

Query Options:
  --query <text>     Search query
  --topK <number>    Number of results (default: 5)
  --debug            Show retrieved chunks and scores

Examples:
  lightrag ingest --file docs/guide.md
  lightrag ingest --text "Some knowledge" --metadata '{"source":"manual"}'
  lightrag query --query "How does routing work?" --debug
  cat document.md | lightrag ingest
  `);
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const command = args[0];

  if (!command || command === 'help') {
    printHelp();
    process.exit(0);
  }

  // Parse flags
  const flags: Record<string, string | boolean> = {};
  for (let i = 1; i < args.length; i++) {
    const arg = args[i]!;
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      const next = args[i + 1];
      if (next && !next.startsWith('--')) {
        flags[key] = next;
        i++;
      } else {
        flags[key] = true;
      }
    } else {
      flags._ = arg;
    }
  }

  switch (command) {
    case 'ingest':
      await ingestCommand({
        file: flags.file as string | undefined,
        text: flags.text as string | undefined,
        metadata: flags.metadata as string | undefined,
        debug: flags.debug === true,
      });
      break;

    case 'query':
      await queryCommand({
        query: (flags.query as string) || (flags._ as string),
        topK: flags.topK ? parseInt(flags.topK as string, 10) : undefined,
        debug: flags.debug === true,
      });
      break;

    case 'stats':
    case 'rebuild':
      log.warn(`${command} command is not yet implemented via CLI. Use the MCP server or programmatic API.`);
      break;

    default:
      log.error(`Unknown command: ${command}`);
      printHelp();
      process.exit(1);
  }
}

main().catch((err) => {
  log.error(`CLI error: ${err}`);
  process.exit(1);
});
