import test from "node:test";
import assert from "node:assert/strict";
import { advisoryUrl, evaluateAudit, exceptionExpires } from "./audit.mjs";

const now = new Date("2026-11-18T12:00:00Z");
const cause = {
  name: "picomatch", dependency: "picomatch", severity: "high",
  url: advisoryUrl, range: "<=4.0.7",
};
const finding = (name, via, severity = "high") => ({
  name, severity, via, nodes: [`node_modules/${name}`],
});
function fixture() {
  const report = {
    auditReportVersion: 2,
    vulnerabilities: {
      picomatch: finding("picomatch", [cause]),
      fdir: finding("fdir", ["picomatch"]),
      vite: finding("vite", ["fdir", "picomatch"]),
    },
  };
  const lock = { packages: Object.fromEntries(Object.keys(report.vulnerabilities).map(name => [
    `node_modules/${name}`, { dev: true, version: name === "picomatch" ? "4.0.7" : "1.0.0" },
  ])) };
  return { report, lock };
}
function evaluate(report, lock, date = now) {
  report.metadata = { vulnerabilities: {
    high: Object.values(report.vulnerabilities).filter(f => f.severity === "high").length,
    critical: Object.values(report.vulnerabilities).filter(f => f.severity === "critical").length,
  } };
  return evaluateAudit(report, lock, date);
}

test("accepts only the named advisory and its solely affected development dependents", () => {
  const { report, lock } = fixture();
  const original = structuredClone({ report, lock });
  const result = evaluate(report, lock);
  assert.deepEqual(result.excepted, ["picomatch", "fdir", "vite"]);
  assert.deepEqual(result.blocked, []);
  assert.deepEqual(report.vulnerabilities, original.report.vulnerabilities);
  assert.deepEqual(lock, original.lock);
});

test("another advisory on the same package blocks it and all affected dependents", () => {
  const { report, lock } = fixture();
  report.vulnerabilities.picomatch.via.push({ ...cause, url: "https://github.com/advisories/GHSA-other" });
  assert.equal(evaluate(report, lock).blocked.length, 3);
});

test("unrelated high and critical findings remain blocking", () => {
  for (const severity of ["high", "critical"]) {
    const { report, lock } = fixture();
    report.vulnerabilities.other = finding("other", [{ ...cause, name: "other" }], severity);
    lock.packages["node_modules/other"] = { dev: true, version: "1.0.0" };
    assert.deepEqual(evaluate(report, lock).blocked.map(f => f.name), ["other"]);
  }
});

test("mixed advisory paths do not exempt the parent", () => {
  const { report, lock } = fixture();
  report.vulnerabilities.vite.via.push({ ...cause, name: "vite", dependency: "vite" });
  assert.deepEqual(evaluate(report, lock).blocked.map(f => f.name), ["vite"]);
});

test("production picomatch and missing development markers are never excepted", () => {
  for (const change of [false, undefined]) {
    const { report, lock } = fixture();
    lock.packages["node_modules/picomatch"].dev = change;
    assert.equal(evaluate(report, lock).blocked.length, 3);
  }
});

test("production ancestor and mixed installed copies remain blocking", () => {
  const { report, lock } = fixture();
  lock.packages["node_modules/vite"].dev = false;
  assert.deepEqual(evaluate(report, lock).blocked.map(f => f.name), ["vite"]);
  report.vulnerabilities.picomatch.nodes.push("node_modules/production/node_modules/picomatch");
  lock.packages["node_modules/production/node_modules/picomatch"] = { version: "4.0.7" };
  assert.equal(evaluate(report, lock).blocked.length, 3);
});

test("version changes, advisory range changes and severity escalations need reassessment", () => {
  for (const update of [
    ({ lock }) => { lock.packages["node_modules/picomatch"].version = "4.0.8"; },
    ({ report }) => { report.vulnerabilities.picomatch.via = [{ ...cause, range: "*" }]; },
    ({ report }) => { report.vulnerabilities.picomatch.severity = "critical"; },
  ]) {
    const data = fixture(); update(data);
    assert.equal(evaluate(data.report, data.lock).blocked.length, 3);
  }
});

test("exception stops working at its expiration boundary", () => {
  const { report, lock } = fixture();
  assert.equal(evaluate(report, lock, new Date(exceptionExpires)).blocked.length, 3);
});

test("unknown and cyclic dependency paths remain blocking", () => {
  for (const dependency of ["missing", "vite"]) {
    const { report, lock } = fixture();
    report.vulnerabilities.vite.via = [dependency];
    assert.deepEqual(evaluate(report, lock).blocked.map(f => f.name), ["vite"]);
  }
});

test("malformed, error and incomplete reports fail closed", () => {
  const { report, lock } = fixture();
  evaluate(report, lock);
  for (const invalid of [null, {}, { ...report, error: { code: "NETWORK" } },
    { ...report, auditReportVersion: 3 }, { ...report, metadata: {} },
    { ...report, vulnerabilities: [] },
    { ...report, vulnerabilities: { picomatch: { ...report.vulnerabilities.picomatch, via: [] } } },
  ]) assert.throws(() => evaluateAudit(invalid, lock, now));
  assert.throws(() => evaluateAudit(report, {}, now));
  assert.throws(() => evaluateAudit(report, lock, new Date("invalid")));
});

test("a clean report passes even after exception expiry", () => {
  assert.deepEqual(evaluate({ auditReportVersion: 2, vulnerabilities: {} }, { packages: {} }, new Date("2027-01-01")), {
    excepted: [], blocked: [],
  });
});
