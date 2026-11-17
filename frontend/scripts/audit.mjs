import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";

export const advisoryUrl = "https://github.com/advisories/GHSA-fc5q-39xc-vjpf";
export const exceptionExpires = "2026-12-02T00:00:00Z";

// Temporary acceptance of a build/test-only dependency with no published fix.
// See docs/frontend-audit.md. Never apply this exception to production dependencies.
export function evaluateAudit(report, lock, now = new Date()) {
  if (report?.error || report?.auditReportVersion !== 2 ||
      !report.vulnerabilities || typeof report.vulnerabilities !== "object" ||
      Array.isArray(report.vulnerabilities) || !lock?.packages ||
      !Number.isFinite(now.getTime())) {
    throw new Error("Unsupported or incomplete npm audit report / lockfile");
  }
  const findings = Object.entries(report.vulnerabilities);
  for (const [name, finding] of findings) {
    if (!finding || finding.name !== name ||
        !["info", "low", "moderate", "high", "critical"].includes(finding.severity) ||
        !Array.isArray(finding.via) || !finding.via.length ||
        !Array.isArray(finding.nodes) || !finding.nodes.length) {
      throw new Error(`Incomplete audit finding: ${name}`);
    }
  }
  for (const severity of ["high", "critical"]) {
    if (report.metadata?.vulnerabilities?.[severity] !==
        findings.filter(([, finding]) => finding.severity === severity).length) {
      throw new Error("Audit severity counts do not match findings");
    }
  }
  function isExcepted(name, ancestors = new Set()) {
    const finding = report.vulnerabilities[name];
    if (!finding || finding.severity !== "high" || ancestors.has(name) || now >= new Date(exceptionExpires) ||
        !finding.nodes.every(node => lock.packages[node]?.dev === true)) return false;
    const chain = new Set([...ancestors, name]);
    return finding.via.every(cause => {
      if (typeof cause === "string") return isExcepted(cause, chain);
      return cause && name === "picomatch" && finding.severity === "high" &&
        cause.name === "picomatch" && cause.dependency === "picomatch" &&
        cause.severity === "high" && cause.url === advisoryUrl &&
        cause.range === "<=4.0.7" &&
        finding.nodes.every(node => lock.packages[node].version === "4.0.7");
    });
  }
  const high = findings.filter(([, finding]) => ["high", "critical"].includes(finding.severity));
  return {
    excepted: high.filter(([name]) => isExcepted(name)).map(([name]) => name),
    blocked: high.filter(([name]) => !isExcepted(name)).map(([name, finding]) => ({ name, ...finding })),
  };
}

function main() {
  const cwd = fileURLToPath(new URL("../", import.meta.url));
  const result = spawnSync(process.platform === "win32" ? "npm.cmd" : "npm",
    ["audit", "--json", "--audit-level=high"],
    { cwd, encoding: "utf8", maxBuffer: 10 * 1024 * 1024 });
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.error || result.signal || ![0, 1].includes(result.status)) {
    throw new Error(`npm audit failed: ${result.error?.message || result.signal || result.status}`);
  }
  const report = JSON.parse(result.stdout);
  const lock = JSON.parse(readFileSync(new URL("../package-lock.json", import.meta.url), "utf8"));
  const { excepted, blocked } = evaluateAudit(report, lock);
  console.log("npm audit vulnerability totals:", report.metadata.vulnerabilities);
  if (excepted.length) {
    console.warn(`TEMPORARY EXCEPTION: ${advisoryUrl} (expires ${exceptionExpires})`);
    console.warn(`Build/test-only picomatch@4.0.7 and solely affected dependents: ${excepted.join(", ")}`);
    console.warn("This exception does not patch the dependency. See docs/frontend-audit.md.");
  }
  if (blocked.length) {
    console.error("Blocking high/critical findings:", JSON.stringify(blocked, null, 2));
    process.exitCode = 1;
  } else {
    console.log("No unexcepted high/critical findings.");
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try { main(); }
  catch (error) { console.error(`Audit failed: ${error.message}`); process.exitCode = 1; }
}
