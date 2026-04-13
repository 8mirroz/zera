#!/usr/bin/env node

import fs from "fs";
import path from "path";

function parseArgs(argv) {
  const args = { taskType: null, complexity: null, config: null };
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    const value = argv[i + 1];
    if (key === "--task-type") {
      args.taskType = value;
      i += 1;
    } else if (key === "--complexity") {
      args.complexity = value;
      i += 1;
    } else if (key === "--config") {
      args.config = value;
      i += 1;
    }
  }
  return args;
}

function usage() {
  const msg = [
    "Usage:",
    "  mcp-profile --task-type T4 --complexity C4 [--config path]",
  ].join("\n");
  console.error(msg);
}

function loadConfig(configPath) {
  const raw = fs.readFileSync(configPath, "utf-8");
  return JSON.parse(raw);
}

function resolveConfigPath(passedPath) {
  if (passedPath) return path.resolve(process.cwd(), passedPath);
  const defaultPath = path.resolve(process.cwd(), "configs/tooling/mcp_profiles.json");
  return defaultPath;
}

function matchRule(rule, taskType, complexity) {
  const taskOk = Array.isArray(rule.task_type) && rule.task_type.includes(taskType);
  const compOk = Array.isArray(rule.complexity) && rule.complexity.includes(complexity);
  return taskOk && compOk;
}

function main() {
  const args = parseArgs(process.argv);
  if (!args.taskType || !args.complexity) {
    usage();
    process.exit(1);
  }

  const configPath = resolveConfigPath(args.config);
  if (!fs.existsSync(configPath)) {
    console.error(`Config not found: ${configPath}`);
    process.exit(1);
  }

  const config = loadConfig(configPath);
  const rules = Array.isArray(config.routing) ? config.routing : [];
  let matchedRule = null;
  let profileName = config.default_profile || "core";

  for (const rule of rules) {
    if (matchRule(rule, args.taskType, args.complexity)) {
      matchedRule = rule;
      profileName = rule.profile;
      break;
    }
  }

  const profile = config.profiles?.[profileName];
  if (!profile) {
    console.error(`Profile not found: ${profileName}`);
    process.exit(1);
  }

  const output = {
    profile: profileName,
    servers: profile.servers || [],
    optional_servers: profile.optional_servers || [],
    allowlist: config.allowlist || [],
    matched_rule: matchedRule
  };

  process.stdout.write(JSON.stringify(output, null, 2));
}

main();
