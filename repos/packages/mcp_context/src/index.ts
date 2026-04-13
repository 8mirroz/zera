import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { readContext } from "./readContext.js";

const server = new Server(
    {
        name: "mcp-antigravity-context",
        version: "1.0.0",
    },
    {
        capabilities: {
            tools: {},
        },
    }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "get_antigravity_context",
                description: "Fetch dynamic rules and configuration from Antigravity OS core layers (e.g. routing, standards, security). Pass the topic name in the query.",
                inputSchema: {
                    type: "object",
                    properties: {
                        query: {
                            type: "string",
                            description: "The exact topic to retrieve. Examples: 'routing', 'roles', 'workspace', or add the 'full' suffix for raw dumps such as 'routing full'.",
                        },
                    },
                    required: ["query"],
                },
            },
        ],
    };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
    if (request.params.name === "get_antigravity_context") {
        const query = String(request.params.arguments?.query || "");
        const contextData = await readContext(query);
        return {
            content: [
                {
                    type: "text",
                    text: contextData,
                },
            ],
        };
    }

    throw new Error("Tool not found");
});

async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("Antigravity Context Engine MCP Server running on stdio");
}

main().catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
});
