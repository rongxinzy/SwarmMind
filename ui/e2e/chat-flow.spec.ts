import { test, expect } from "@playwright/test";

const CHAT_URL = process.env.CHAT_URL || "http://localhost:3000";

test.describe("SwarmMind Chat Flow", () => {
  test("complete conversation flow — login, send message, receive AI response", async ({
    page,
  }) => {
    test.setTimeout(120_000);

    // ── 1. Navigate to app ──────────────────────────────────────
    await page.goto(CHAT_URL, { waitUntil: "networkidle" });

    // ── 2. Login (initial admin setup or direct login) ──────────
    // If setup page is shown (first run), create the admin account
    const isSetup = await page
      .getByRole("button", { name: /创建账号|初始化/i })
      .isVisible()
      .catch(() => false);

    if (isSetup) {
      await page.getByLabel(/邮箱/i).fill("e2e@swarmmind.dev");
      await page.getByLabel(/密码/i).fill("e2etest123");
      const displayNameInput = page.getByLabel(/显示名称/i);
      if (await displayNameInput.isVisible()) {
        await displayNameInput.fill("E2E Tester");
      }
      await page.getByRole("button", { name: /创建账号|初始化/i }).click();
    } else {
      await page.getByLabel(/邮箱/i).fill("e2e@swarmmind.dev");
      await page.getByLabel(/密码/i).fill("e2etest123");
      await page.getByRole("button", { name: /登录/i }).click();
    }

    // Wait for the main app shell (sidebar + chat area)
    await expect(page.getByText("SwarmMind")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("开始对话")).toBeVisible({ timeout: 10_000 });

    // ── 3. Send a chat message ──────────────────────────────────
    const textarea = page.getByPlaceholder(/消息/i);
    await expect(textarea).toBeVisible({ timeout: 5_000 });
    await textarea.fill("请用一句话介绍你自己。");
    
    // Click submit button
    const submitBtn = page.locator('button[type="submit"]');
    await expect(submitBtn).toBeEnabled({ timeout: 5_000 });
    await submitBtn.click();

    // ── 4. Wait for streaming response ───────────────────────────
    // The submit button should transition (streaming state)
    // Wait for the assistant message to appear
    await page.waitForTimeout(2_000);

    // Verify a response appeared (MessageResponse renders markdown content)
    // Wait up to 60 seconds for the AI to respond
    const responseArea = page.locator('[class*="is-assistant"]').first();
    await expect(responseArea).toBeVisible({ timeout: 60_000 });

    // ── 5. Verify the conversation persists (history) ────────────
    // Reload the page and verify the conversation appears in history
    await page.reload({ waitUntil: "networkidle" });
    
    // The sidebar should show the conversation
    const historyItem = page.getByText("请用一句话介绍你自己");
    await expect(historyItem).toBeVisible({ timeout: 10_000 });

    // Click the history item to reload the conversation
    await historyItem.click();
    await page.waitForTimeout(2_000);

    // Verify the message still renders after reload
    const reloadedResponse = page.locator('[class*="is-assistant"]').first();
    await expect(reloadedResponse).toBeVisible({ timeout: 10_000 });
  });
});
