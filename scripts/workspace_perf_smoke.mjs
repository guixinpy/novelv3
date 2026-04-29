#!/usr/bin/env node
import { spawnSync } from 'node:child_process'

function readArg(name, fallback = '') {
  const index = process.argv.indexOf(name)
  return index >= 0 ? process.argv[index + 1] || fallback : fallback
}

const baseUrl = readArg('--base-url', 'http://localhost:8001').replace(/\/$/, '')
const projectId = readArg('--project-id')
const session = readArg('--session', `workspace-perf-${Date.now()}`)

if (!projectId) {
  console.error('Usage: node scripts/workspace_perf_smoke.mjs --project-id <id> [--base-url http://localhost:8001] [--session name]')
  process.exit(2)
}

function runAgent(args, input = '') {
  const result = spawnSync('agent-browser', ['--session', session, ...args], {
    input,
    encoding: 'utf8',
  })
  if (result.status !== 0) {
    throw new Error(`${['agent-browser', ...args].join(' ')} failed\n${result.stderr || result.stdout}`)
  }
  return result.stdout.trim()
}

function extractJson(text) {
  const start = text.indexOf('{')
  if (start < 0) throw new Error(`agent-browser output did not contain JSON:\n${text}`)
  return JSON.parse(text.slice(start))
}

const evalSource = `
(async () => {
const baseUrl = ${JSON.stringify(baseUrl)};
const projectId = ${JSON.stringify(projectId)};
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
if (!window.__workspacePerfOriginalFetch) window.__workspacePerfOriginalFetch = window.fetch.bind(window);
window.__workspacePerfRecords = [];
window.__workspacePerfPhase = 'idle';
window.__workspacePerfInFlight = 0;
function normalizeUrl(value) {
  try {
    const parsed = new URL(String(value), baseUrl);
    return parsed.pathname + parsed.search;
  } catch {
    return String(value);
  }
}
window.fetch = async (...args) => {
  const request = args[0];
  const url = typeof request === 'string' ? request : request?.url || '';
  const method = args[1]?.method || request?.method || 'GET';
  const phase = window.__workspacePerfPhase || 'unknown';
  const start = performance.now();
  window.__workspacePerfInFlight += 1;
  try {
    const response = await window.__workspacePerfOriginalFetch(...args);
    if (String(url).includes('/api/')) {
      window.__workspacePerfRecords.push({
        phase,
        method,
        url: normalizeUrl(url),
        status: response.status,
        durationMs: Math.round(performance.now() - start),
      });
    }
    return response;
  } finally {
    window.__workspacePerfInFlight -= 1;
  }
};
async function waitQuiet() {
  let quietSince = performance.now();
  const deadline = performance.now() + 7000;
  while (performance.now() < deadline) {
    if (window.__workspacePerfInFlight === 0) {
      if (performance.now() - quietSince > 350) return;
    } else {
      quietSince = performance.now();
    }
    await delay(50);
  }
}
async function go(phase, path) {
  window.__workspacePerfPhase = phase;
  window.history.pushState({}, '', path);
  window.dispatchEvent(new PopStateEvent('popstate'));
  await waitQuiet();
}
await go('cold_hermes', '/projects/' + projectId + '/hermes');
await go('hermes_to_athena', '/projects/' + projectId + '/athena');
await go('athena_to_hermes', '/projects/' + projectId + '/hermes');
window.__workspacePerfPhase = 'rapid_switch';
for (const path of [
  '/projects/' + projectId + '/athena',
  '/projects/' + projectId + '/hermes',
  '/projects/' + projectId + '/manuscript',
  '/projects/' + projectId + '/hermes',
  '/projects/' + projectId + '/athena',
  '/projects/' + projectId + '/manuscript',
  '/projects/' + projectId + '/hermes',
]) {
  window.history.pushState({}, '', path);
  window.dispatchEvent(new PopStateEvent('popstate'));
  await delay(120);
}
await waitQuiet();
const summary = {};
for (const record of window.__workspacePerfRecords) {
  const item = summary[record.phase] || { requestCount: 0, totalDurationMs: 0, urls: [], duplicateUrls: [] };
  item.requestCount += 1;
  item.totalDurationMs += record.durationMs;
  item.urls.push(record.url);
  summary[record.phase] = item;
}
for (const item of Object.values(summary)) {
  const counts = new Map();
  for (const url of item.urls) counts.set(url, (counts.get(url) || 0) + 1);
  item.duplicateUrls = [...counts.entries()].filter(([, count]) => count > 1).map(([url]) => url);
}
return summary;
})()
`

runAgent(['open', `${baseUrl}/`])
runAgent(['wait', '--load', 'networkidle'])
const summary = extractJson(runAgent(['eval', '--stdin'], evalSource))

const thresholds = {
  cold_hermes: 1,
  hermes_to_athena: 2,
  athena_to_hermes: 1,
  rapid_switch: 8,
}
const failures = Object.entries(thresholds).flatMap(([phase, max]) => {
  const count = summary[phase]?.requestCount || 0
  return count > max ? [`${phase} requestCount ${count} > ${max}`] : []
})

const result = { baseUrl, projectId, session, thresholds, summary, failures }
console.log(JSON.stringify(result, null, 2))
if (failures.length) process.exit(1)
