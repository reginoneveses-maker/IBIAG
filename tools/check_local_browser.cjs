const {chromium} = require(process.env.LOCAL_PLAYWRIGHT_PATH);
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage();
    const outside = [];
    await page.route("**/*", route => {
      const url = new URL(route.request().url());
      if (url.origin === "http://127.0.0.1:8787") return route.continue();
      outside.push(url.hostname);
      return route.abort();
    });
    await page.goto("http://127.0.0.1:8787", {waitUntil: "networkidle"});
    await page.getByTestId("login-email-input").fill(process.env.LOCAL_TEST_EMAIL);
    await page.getByTestId("login-password-input").fill(process.env.LOCAL_TEST_PASSWORD);
    const login = page.waitForResponse(r => r.url().endsWith("/api/auth/login") && r.request().method() === "POST");
    await page.getByTestId("login-submit-button").click();
    assert.equal((await login).status(), 200);
    await page.waitForURL("http://127.0.0.1:8787/");
    await page.waitForLoadState("networkidle");
    assert.equal(await page.getByTestId("login-page").count(), 0);
    assert.equal(await page.locator("body").evaluate(el => el.scrollWidth <= innerWidth), true);
    assert.equal(outside.length, 0, "local shell requested an external resource");
    console.log("PASS: actual browser login with external network blocked");
  } finally {await browser.close();}
})().catch(() => {console.error("Local browser smoke failed; no credentials logged.");process.exit(1);});
