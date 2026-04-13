// MCP Server — LightRAG as Model Context Protocol server

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { createPipeline, LightRagPipeline } from './pipelines/pipeline.js';
import { DEFAULT_CONFIG, LightRagConfig } from './config/types.js';
import { createLogger, Logger } from './utils/logger.js';

const log = createLogger('mcp-server');

let pipeline: LightRagPipeline | null = null;

async function getPipeline(): Promise<LightRagPipeline> {
  if (!pipeline) {
    // Allow config override via environment
    const config: LightRagConfig = { ...DEFAULT_CONFIG };

    if (process.env.LIGHTRAG_DATA_DIR) {
      config.storage.dataDir = process.env.LIGHTRAG_DATA_DIR;
    }
    if (process.env.LIGHTRAG_DEBUG) {
      config.debug = process.env.LIGHTRAG_DEBUG === 'true';
    }
    if (process.env.LIGHTRAG_TOP_K) {
      config.retrieval.topK = parseInt(process.env.LIGHTRAG_TOP_K, 10);
    }
    if (process.env.LIGHTRAG_EMBEDDING_PROVIDER) {
      config.embedding.provider = process.env.LIGHTRAG_EMBEDDING_PROVIDER as any;
    }
    if (process.env.LIGHTRAG_GENERATOR_PROVIDER) {
      config.generation.provider = process.env.LIGHTRAG_GENERATOR_PROVIDER as any;
    }
    if (process.env.LIGHTRAG_GENERATOR_MODEL) {
      config.generation.model = process.env.LIGHTRAG_GENERATOR_MODEL;
    }
    if (process.env.LIGHTRAG_API_KEY) {
      config.embedding.apiKey = process.env.LIGHTRAG_API_KEY;
      config.generation.apiKey = process.env.LIGHTRAG_API_KEY;
    }
    if (process.env.LIGHTRAG_ENDPOINT) {
      config.embedding.endpoint = process.env.LIGHTRAG_ENDPOINT;
      config.generation.endpoint = process.env.LIGHTRAG_ENDPOINT;
    }

    pipeline = await createPipeline(config);
  }
  return pipeline;
}

const server = new Server(
  {
    name: 'lightrag',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  },
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'lightrag_ingest_documents',
        description: 'Ingest documents into the LightRAG knowledge base. Supports text content with optional metadata. Documents are chunked and embedded automatically.',
        inputSchema: {
          type: 'object',
          properties: {
            content: {
              type: 'string',
              description: 'The document content to ingest',
            },
            metadata: {
              type: 'string',
              description: 'JSON string of metadata key-value pairs',
            },
          },
          required: ['content'],
        },
      },
      {
        name: 'lightrag_query_knowledge',
        description: 'Query the LightRAG knowledge base. Returns an AI-generated answer based on retrieved context. Use debug=true to see retrieved chunks.',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'The search query or question',
            },
            topK: {
              type: 'number',
              description: 'Number of top results to retrieve (default: 5)',
            },
            debug: {
              type: 'boolean',
              description: 'Show retrieved chunks and scores for debugging',
            },
          },
          required: ['query'],
        },
      },
      {
        name: 'lightrag_rebuild_index',
        description: 'Rebuild the LightRAG index from storage. Use after manual data changes or to refresh the in-memory cache.',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
      {
        name: 'lightrag_stats',
        description: 'Get statistics about the LightRAG knowledge base (documents, chunks, embeddings, cache size).',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const p = await getPipeline();

  switch (request.params.name) {
    case 'lightrag_ingest_documents': {
      const content = String(request.params.arguments?.content || '');
      const metadataStr = String(request.params.arguments?.metadata || '{}');

      if (!content) {
        return {
          content: [{ type: 'text', text: JSON.stringify({ error: 'Content is required' }) }],
          isError: true,
        };
      }

      let metadata: Record<string, unknown>;
      try {
        metadata = JSON.parse(metadataStr);
      } catch {
        return {
          content: [{ type: 'text', text: JSON.stringify({ error: 'Invalid metadata JSON' }) }],
          isError: true,
        };
      }

      const result = await p.ingest(content, metadata);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    }

    case 'lightrag_query_knowledge': {
      const query = String(request.params.arguments?.query || '');
      const topK = request.params.arguments?.topK ? Number(request.params.arguments.topK) : undefined;
      const debug = Boolean(request.params.arguments?.debug);

      if (!query) {
        return {
          content: [{ type: 'text', text: JSON.stringify({ error: 'Query is required' }) }],
          isError: true,
        };
      }

      const response = await p.query(query, {
        topK: topK ?? p['config'].retrieval.topK,
        debug,
      });

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            answer: response.answer,
            latency: response.latency,
            resultCount: response.results.length,
            ...(debug && response.debugInfo ? { debug: response.debugInfo } : {}),
          }, null, 2),
        }],
      };
    }

    case 'lightrag_rebuild_index': {
      const result = await p.rebuildIndex();
      return {
        content: [{ type: 'text', text: JSON.stringify({ success: true, ...result }, null, 2) }],
      };
    }

    case 'lightrag_stats': {
      const stats = await p.stats();
      return {
        content: [{ type: 'text', text: JSON.stringify(stats, null, 2) }],
      };
    }

    default:
      return {
        content: [{ type: 'text', text: `Unknown tool: ${request.params.name}` }],
        isError: true,
      };
  }
});

async function main(): Promise<void> {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  log.info('LightRAG MCP Server running on stdio');

  // Graceful shutdown
  process.on('SIGINT', async () => {
    log.info('Shutting down...');
    if (pipeline) {
      await pipeline.shutdown();
    }
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    log.info('Shutting down...');
    if (pipeline) {
      await pipeline.shutdown();
    }
    process.exit(0);
  });
}

main().catch((error) => {
  log.error(`Fatal error: ${error}`);
  process.exit(1);
});
