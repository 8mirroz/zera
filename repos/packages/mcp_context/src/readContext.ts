import * as fs from 'fs/promises';
import * as path from 'path';

const CORE_DIR = process.env.ANTIGRAVITY_CORE_DIR || path.join(process.env.HOME || '', 'antigravity-core');
const TOPICS = ['routing', 'standards', 'security', 'meta_prompt', 'workspace', 'roles', 'qwen'] as const;
type TopicName = (typeof TOPICS)[number];

const CONTEXT_MAPPING: Record<TopicName, string[]> = {
    routing: [
        'configs/orchestrator/router.yaml',
        'configs/orchestrator/models.yaml',
        'configs/orchestrator/completion_gates.yaml',
        'configs/rules/TASK_ROUTING.md',
    ],
    standards: [
        'configs/rules/ENGINEERING_STANDARDS.md',
        'configs/rules/BUILD_PROFILE.md',
        'configs/rules/ANTI_CHAOS.md',
    ],
    security: [
        'configs/rules/SECURITY_RULES.md',
    ],
    meta_prompt: [
        'configs/rules/META_PROMPT.md',
    ],
    workspace: [
        'RULES.md',
        'configs/rules/WORKSPACE_STANDARD.md',
        'configs/rules/GLOBAL_RULE_RU.md',
    ],
    roles: [
        'configs/orchestrator/AGENT_ROLE_CONTRACTS.md',
        'configs/rules/AGENT_ONLY.md',
    ],
    qwen: [
        'configs/rules/QWEN.md',
        'configs/tooling/qwen_context_agent.json',
    ],
};

type TopicRequest = {
    topic: TopicName;
    mode: 'summary' | 'full';
};

type FilePayload = {
    path: string;
    content?: string;
    error?: string;
};

function normalizeQueryChunk(chunk: string): TopicRequest | null {
    const trimmed = chunk.trim().toLowerCase();
    if (!trimmed) {
        return null;
    }

    let mode: 'summary' | 'full' = 'summary';
    let topicCandidate = trimmed;
    const fullSuffixMatch = trimmed.match(/^(.*?)(?::full|\/full|\s+full)$/);
    if (fullSuffixMatch) {
        topicCandidate = fullSuffixMatch[1].trim();
        mode = 'full';
    }

    if ((TOPICS as readonly string[]).includes(topicCandidate)) {
        return { topic: topicCandidate as TopicName, mode };
    }
    return null;
}

function parseTopicRequests(query: string): TopicRequest[] {
    const chunks = query.split(/[,\n]+/g);
    const requests = chunks
        .map((chunk) => normalizeQueryChunk(chunk))
        .filter((item): item is TopicRequest => Boolean(item));

    const deduped = new Map<TopicName, TopicRequest>();
    for (const request of requests) {
        deduped.set(request.topic, request);
    }
    return Array.from(deduped.values());
}

function expandEnvVars(text: string): string {
    return text.replace(/\$([A-Z0-9_]+)|\$\{([A-Z0-9_]+)\}/g, (match, p1, p2) => {
        const varName = p1 || p2;
        return process.env[varName] !== undefined ? process.env[varName] : match;
    });
}

function compactLine(line: string): string {
    return line
        .replace(/[`*_>#|]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function collectMatches(content: string, pattern: RegExp, limit = 8): string[] {
    const out: string[] = [];
    for (const match of content.matchAll(pattern)) {
        const value = compactLine(match[1] || '');
        if (value && !out.includes(value)) {
            out.push(value);
        }
        if (out.length >= limit) {
            break;
        }
    }
    return out;
}

function countYamlEntries(content: string, sectionName: string): number {
    const lines = content.split('\n');
    let insideSection = false;
    let count = 0;

    for (const line of lines) {
        if (!insideSection) {
            if (line.trim() === `${sectionName}:`) {
                insideSection = true;
            }
            continue;
        }

        if (line && !line.startsWith(' ')) {
            break;
        }
        if (/^\s{2}AGENT_MODEL_[A-Z0-9_]+:/.test(line)) {
            count += 1;
        }
    }

    return count;
}

function summarizeRouting(files: FilePayload[]): Record<string, unknown> {
    const router = files.find((file) => file.path.endsWith('router.yaml'))?.content || '';
    const models = files.find((file) => file.path.endsWith('models.yaml'))?.content || '';
    const gates = files.find((file) => file.path.endsWith('completion_gates.yaml'))?.content || '';

    const routerVersion = router.match(/^version:\s*"?([^"\n]+)"?/m)?.[1] || null;
    const tiers = collectMatches(router, /^\s{4}(C[1-5]):/gm, 5);
    const taskTypes = collectMatches(router, /^\s{4}(T[1-7]):/gm, 7);
    const paths = collectMatches(router, /^\s{6}path:\s*"([^"\n]+)"/gm, 6);
    const canonicalAliases = countYamlEntries(models, 'aliases');
    const compatAliases = countYamlEntries(models, 'compat_aliases');
    const gateTiers = collectMatches(gates, /^\s{2}(C[1-5]):/gm, 5);

    return {
        routerVersion,
        tiers,
        taskTypes,
        paths,
        canonicalAliases,
        compatAliases,
        completionGateTiers: gateTiers,
    };
}

function summarizeRoles(files: FilePayload[]): Record<string, unknown> {
    const contracts = files.find((file) => file.path.endsWith('AGENT_ROLE_CONTRACTS.md'))?.content || '';
    const roles = collectMatches(contracts, /^\| \*\*(.+?)\*\* \|/gm, 12);
    const obligations = collectMatches(contracts, /^- Verification:\s+(.+)$/gm, 12);
    return {
        roles,
        roleCount: roles.length,
        verificationHighlights: obligations.slice(0, 5),
    };
}

function summarizeGeneric(files: FilePayload[]): Record<string, unknown> {
    const headings = files.flatMap((file) => collectMatches(file.content || '', /^#{1,3}\s+(.+)$/gm, 6)).slice(0, 8);
    const bullets = files.flatMap((file) => collectMatches(file.content || '', /^\s*[-*]\s+(.+)$/gm, 6)).slice(0, 8);
    return {
        headings,
        bullets,
    };
}

function summarizeTopic(topic: TopicName, files: FilePayload[]): Record<string, unknown> {
    if (topic === 'routing') {
        return summarizeRouting(files);
    }
    if (topic === 'roles') {
        return summarizeRoles(files);
    }
    return summarizeGeneric(files);
}

async function loadTopicFiles(topic: TopicName): Promise<FilePayload[]> {
    const files = CONTEXT_MAPPING[topic];
    const payloads = await Promise.all(
        files.map(async (relPath): Promise<FilePayload> => {
            const fullPath = path.join(CORE_DIR, relPath);
            try {
                let content = await fs.readFile(fullPath, 'utf8');
                if (topic === 'routing') {
                    content = expandEnvVars(content);
                }
                return { path: relPath, content };
            } catch (err: unknown) {
                return {
                    path: relPath,
                    error: err instanceof Error ? err.message : 'could not read file',
                };
            }
        }),
    );
    return payloads;
}

function renderRawTopic(topic: TopicName, files: FilePayload[]): string {
    let output = `\n\n--- CONTEXT: ${topic.toUpperCase()} ---\n`;
    for (const file of files) {
        if (file.error) {
            output += `\nFile: ${file.path} (Error: ${file.error})\n`;
            continue;
        }
        output += `\nFile: ${file.path}\n${file.content || ''}\n`;
    }
    return output;
}

export async function readContext(query: string): Promise<string> {
    const requests = parseTopicRequests(query);

    if (requests.length === 0) {
        return JSON.stringify(
            {
                status: 'error',
                message: `Unknown context requested: '${query}'`,
                availableTopics: TOPICS,
                usage: [
                    'routing',
                    'roles',
                    'workspace',
                    'routing full',
                    'routing,roles',
                ],
            },
            null,
            2,
        );
    }

    const topicPayloads = await Promise.all(
        requests.map(async (request) => {
            const files = await loadTopicFiles(request.topic);
            return {
                topic: request.topic,
                mode: request.mode,
                files,
            };
        }),
    );

    if (topicPayloads.every((item) => item.mode === 'full')) {
        return topicPayloads.map((item) => renderRawTopic(item.topic, item.files)).join('');
    }

    const envelope = {
        version: 'orchestrator_v5',
        mode: 'summary',
        topics: topicPayloads.map((item) => ({
            topic: item.topic,
            files: item.files.map((file) => ({
                path: file.path,
                status: file.error ? 'error' : 'ok',
            })),
            summary: summarizeTopic(item.topic, item.files),
            rawModeAvailable: `${item.topic} full`,
        })),
    };

    return JSON.stringify(envelope, null, 2);
}
