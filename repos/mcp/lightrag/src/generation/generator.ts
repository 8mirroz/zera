// Generator — LLM provider abstraction for answer generation

import { GenerationConfig } from '../config/types.js';
import { RetrievalResult } from '../types.js';
import { createLogger, Logger } from '../utils/logger.js';

export interface Generator {
  generate(query: string, context: RetrievalResult[]): Promise<string>;
}

const DEFAULT_SYSTEM_PROMPT = `You are a knowledgeable assistant that answers questions based on provided context.
Rules:
1. Always base your answer on the context provided
2. If the context doesn't contain enough information, say so explicitly
3. Be concise and precise
4. Use markdown formatting for code blocks and technical terms
5. Cite specific parts of the context when possible
6. If context contains multiple relevant viewpoints, present them all
7. Answer in the same language as the question`;

export class OpenAiGenerator implements Generator {
  private log: Logger;
  private endpoint: string;
  private headers: Record<string, string>;

  constructor(private config: GenerationConfig) {
    this.log = createLogger('generator-openai');
    this.endpoint = config.endpoint || 'https://api.openai.com/v1/chat/completions';
    this.headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${config.apiKey}`,
    };
  }

  async generate(query: string, context: RetrievalResult[]): Promise<string> {
    const prompt = this.buildPrompt(query, context);

    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        model: this.config.model,
        messages: [
          { role: 'system', content: this.config.systemPrompt || DEFAULT_SYSTEM_PROMPT },
          { role: 'user', content: prompt },
        ],
        max_tokens: this.config.maxTokens,
        temperature: this.config.temperature,
      }),
    });

    if (!response.ok) {
      throw new Error(`OpenAI API error: ${response.status} ${response.statusText}`);
    }

    const data: { choices: Array<{ message: { content: string } }> } = await response.json();
    return data.choices[0]?.message.content || 'No response generated';
  }

  private buildPrompt(query: string, context: RetrievalResult[]): string {
    const contextText = context
      .map((r, i) => `[Context ${i + 1}] (score: ${r.score.toFixed(3)})\n${r.chunk.content}`)
      .join('\n\n');

    return `Context:
${contextText}

Question: ${query}

Answer based on the context above:`;
  }
}

export class GeminiGenerator implements Generator {
  private log: Logger;
  private endpoint: string;
  private headers: Record<string, string>;

  constructor(private config: GenerationConfig) {
    this.log = createLogger('generator-gemini');
    this.endpoint = config.endpoint ||
      `https://generativelanguage.googleapis.com/v1beta/models/${config.model}:generateContent?key=${config.apiKey}`;
    this.headers = { 'Content-Type': 'application/json' };
  }

  async generate(query: string, context: RetrievalResult[]): Promise<string> {
    const prompt = this.buildPrompt(query, context);

    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        contents: [{
          parts: [{ text: prompt }],
        }],
        generationConfig: {
          maxOutputTokens: this.config.maxTokens,
          temperature: this.config.temperature,
        },
      }),
    });

    if (!response.ok) {
      throw new Error(`Gemini API error: ${response.status} ${response.statusText}`);
    }

    const data: { candidates: Array<{ content: { parts: Array<{ text: string }> } }> } = await response.json();
    return data.candidates[0]?.content.parts[0]?.text || 'No response generated';
  }

  private buildPrompt(query: string, context: RetrievalResult[]): string {
    const contextText = context
      .map((r, i) => `[Context ${i + 1}] (relevance: ${r.score.toFixed(3)})\n${r.chunk.content}`)
      .join('\n\n');

    return `${this.config.systemPrompt || DEFAULT_SYSTEM_PROMPT}

Context:
${contextText}

Question: ${query}

Answer:`;
  }
}

export class OllamaGenerator implements Generator {
  private log: Logger;
  private endpoint: string;

  constructor(private config: GenerationConfig) {
    this.log = createLogger('generator-ollama');
    this.endpoint = (config.endpoint || 'http://localhost:11434') + '/api/chat';
  }

  async generate(query: string, context: RetrievalResult[]): Promise<string> {
    const prompt = this.buildPrompt(query, context);

    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: this.config.model,
        messages: [
          { role: 'system', content: this.config.systemPrompt || DEFAULT_SYSTEM_PROMPT },
          { role: 'user', content: prompt },
        ],
        stream: false,
        options: {
          num_predict: this.config.maxTokens,
          temperature: this.config.temperature,
        },
      }),
    });

    if (!response.ok) {
      throw new Error(`Ollama API error: ${response.status} ${response.statusText}`);
    }

    const data: { message: { content: string } } = await response.json();
    return data.message?.content || 'No response generated';
  }

  private buildPrompt(query: string, context: RetrievalResult[]): string {
    const contextText = context
      .map((r, i) => `[Source ${i + 1}] (relevance: ${(r.score * 100).toFixed(1)}%)\n${r.chunk.content}`)
      .join('\n\n---\n\n');

    return `Here is relevant context:

${contextText}

Now answer this question: ${query}`;
  }
}

export class QwenGenerator implements Generator {
  private log: Logger;
  private endpoint: string;

  constructor(private config: GenerationConfig) {
    this.log = createLogger('generator-qwen');
    // Support both Ollama-based and API-based Qwen
    this.endpoint = config.endpoint || 'http://localhost:11434/api/chat';
  }

  async generate(query: string, context: RetrievalResult[]): Promise<string> {
    const prompt = this.buildPrompt(query, context);

    // Detect if it's an API endpoint or Ollama
    const isOllama = this.endpoint.includes('11434');

    const body = isOllama
      ? {
          model: this.config.model,
          messages: [
            { role: 'system', content: this.config.systemPrompt || DEFAULT_SYSTEM_PROMPT },
            { role: 'user', content: prompt },
          ],
          stream: false,
          options: {
            num_predict: this.config.maxTokens,
            temperature: this.config.temperature,
          },
        }
      : {
          model: this.config.model,
          messages: [
            { role: 'system', content: this.config.systemPrompt || DEFAULT_SYSTEM_PROMPT },
            { role: 'user', content: prompt },
          ],
          max_tokens: this.config.maxTokens,
          temperature: this.config.temperature,
        };

    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`Qwen API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();

    if (isOllama) {
      return (data as any).message?.content || 'No response generated';
    } else {
      return (data as any).choices?.[0]?.message?.content || 'No response generated';
    }
  }

  private buildPrompt(query: string, context: RetrievalResult[]): string {
    const contextText = context
      .map((r, i) => `### Context ${i + 1} (relevance: ${(r.score * 100).toFixed(0)}%)
${r.chunk.content}`)
      .join('\n\n');

    return `You have the following context to answer the question:

${contextText}

Question: ${query}

Provide a detailed answer based on the context.`;
  }
}

export function createGenerator(config: GenerationConfig): Generator {
  switch (config.provider) {
    case 'openai':
      return new OpenAiGenerator(config);
    case 'gemini':
      return new GeminiGenerator(config);
    case 'ollama':
      return new OllamaGenerator(config);
    case 'qwen':
      return new QwenGenerator(config);
    default:
      throw new Error(`Unknown generator provider: ${config.provider}`);
  }
}
