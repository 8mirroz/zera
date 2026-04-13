// Logging utility — structured, low-overhead logging

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

export interface LogEntry {
  timestamp: string;
  level: string;
  module: string;
  message: string;
  data?: Record<string, unknown>;
  duration?: number;
}

export interface Logger {
  debug(message: string, data?: Record<string, unknown>): void;
  info(message: string, data?: Record<string, unknown>): void;
  warn(message: string, data?: Record<string, unknown>): void;
  error(message: string, data?: Record<string, unknown>): void;
  time(label: string): void;
  timeEnd(label: string): number;
  flush(): void;
}

const timers = new Map<string, number>();
const logBuffer: LogEntry[] = [];
const MAX_BUFFER = 500;

function formatEntry(
  level: string,
  module: string,
  message: string,
  data?: Record<string, unknown>,
  duration?: number,
): LogEntry {
  return {
    timestamp: new Date().toISOString(),
    level,
    module,
    message,
    data,
    duration,
  };
}

function output(entry: LogEntry): void {
  const { timestamp, level, module, message, duration } = entry;
  const dur = duration !== undefined ? ` [${duration}ms]` : '';
  const line = `[${timestamp}] ${level.padEnd(5)} [${module}] ${message}${dur}`;

  switch (entry.level) {
    case 'DEBUG':
      // eslint-disable-next-line no-console
      console.debug(line);
      break;
    case 'INFO':
      // eslint-disable-next-line no-console
      console.info(line);
      break;
    case 'WARN':
      // eslint-disable-next-line no-console
      console.warn(line);
      break;
    case 'ERROR':
      // eslint-disable-next-line no-console
      console.error(line);
      break;
  }
}

export function createLogger(module: string, minLevel: LogLevel = LogLevel.INFO): Logger {
  return {
    debug(message: string, data?: Record<string, unknown>): void {
      if (minLevel > LogLevel.DEBUG) return;
      const entry = formatEntry('DEBUG', module, message, data);
      logBuffer.push(entry);
      output(entry);
    },

    info(message: string, data?: Record<string, unknown>): void {
      if (minLevel > LogLevel.INFO) return;
      const entry = formatEntry('INFO', module, message, data);
      logBuffer.push(entry);
      output(entry);
    },

    warn(message: string, data?: Record<string, unknown>): void {
      if (minLevel > LogLevel.WARN) return;
      const entry = formatEntry('WARN', module, message, data);
      logBuffer.push(entry);
      output(entry);
    },

    error(message: string, data?: Record<string, unknown>): void {
      if (minLevel > LogLevel.ERROR) return;
      const entry = formatEntry('ERROR', module, message, data);
      logBuffer.push(entry);
      output(entry);
    },

    time(label: string): void {
      timers.set(label, Date.now());
    },

    timeEnd(label: string): number {
      const start = timers.get(label);
      if (start === undefined) {
        this.warn(`Timer "${label}" not started`);
        return 0;
      }
      const duration = Date.now() - start;
      timers.delete(label);
      return duration;
    },

    flush(): void {
      logBuffer.splice(0, logBuffer.length);
    },
  };
}

export function getBufferSize(): number {
  return logBuffer.length;
}

export function drainBuffer(): LogEntry[] {
  const copy = [...logBuffer];
  logBuffer.length = 0;
  return copy;
}
