import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright-core";

const preview = "http://127.0.0.1:5173";
const output = process.argv[2];
if (!output) throw new Error("Pass a directory for the synthetic verification evidence.");
await mkdir(output, { recursive: true });

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const health = await page.request.get(preview + "/health");
  assert.equal(health.status(), 200);
  assert.equal((await health.json()).mode, "keyless");

  await page.goto(preview);
  await page.getByRole("button", { name: "Create an account", exact: true }).click();
  const password = randomUUID();
  await page.locator("#username").fill("demo-" + randomUUID().slice(0, 8));
  await page.locator("#password").fill(password);
  await page.locator("#confirm-password").fill(password);
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await page.getByText("Keyless · local MiniLM AI", { exact: true }).waitFor();

  const results = [];
  for (const [name, count, policy] of [
    ["Try complete example", "4 of 4", "allowed"],
    ["Try missing-skills example", "1 of 4", "blocked"],
  ]) {
    const uploaded = page.waitForResponse(response =>
      response.url().endsWith("/api/v1/resumes/upload") && response.request().method() === "POST");
    await page.getByRole("button", { name: new RegExp(name) }).click();
    const response = await uploaded;
    assert.equal(response.ok(), true);
    const result = await response.json();
    assert.equal(result.policy_status, policy);
    assert.equal(result.failure_code, null);
    assert.equal(result.requires_human_review, true);
    await page.locator("article.is-open").getByText(count, { exact: true }).waitFor();
    results.push({ evaluationId: result.evaluation_id, skillCount: count, policy });
  }

  const card = page.locator("article.is-open");
  await card.getByRole("checkbox").check();
  await card.getByRole("button", { name: "Needs follow-up", exact: true }).click();
  await card.getByText("Review saved: Follow-up required", { exact: true }).waitFor();
  await page.reload();
  const saved = page.locator("article").filter({ hasText: results[1].evaluationId.slice(-8) });
  await saved.getByRole("button", { name: "View review" }).click();
  await saved.getByText("Review saved: Follow-up required", { exact: true }).waitFor();
  await saved.screenshot({ path: path.join(output, "saved-review.png") });

  await page.getByText("Record lookup & audit tools", { exact: true }).click();
  await page.getByRole("button", { name: "Load saved audits" }).click();
  for (const { evaluationId } of results) {
    await page.locator(".audit-list li").filter({ hasText: evaluationId.slice(-8) }).waitFor();
  }
  await page.locator(".audit-list").screenshot({ path: path.join(output, "audit.png") });
  await page.getByRole("heading", { name: "Your résumé workspace" }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(output, "workspace.png") });
  const summary = {
    revision: process.env.GITHUB_SHA,
    run: process.env.GITHUB_RUN_ID,
    environment: "Ephemeral runner-local preview of the built React app",
    mode: "keyless",
    results,
    followUpSurvivedReload: true,
    bothAuditRecordsVisible: true,
  };
  await writeFile(path.join(output, "preview.json"), JSON.stringify(summary, null, 2) + "\n");
  console.log("Keyless preview passed both synthetic evaluations, review persistence and audit lookup.");
} finally {
  await browser.close();
}
