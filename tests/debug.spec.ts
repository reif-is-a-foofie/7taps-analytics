import { test, expect } from '@playwright/test';

test('debug JavaScript console logs', async ({ page }) => {
  const logs: string[] = [];
  const errors: string[] = [];
  
  // Capture console logs and errors
  page.on('console', msg => {
    logs.push(msg.text());
    console.log('Console:', msg.text());
  });
  
  page.on('pageerror', error => {
    errors.push(error.message);
    console.log('Page Error:', error.message);
  });
  
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  
  // Wait a moment for any delayed JavaScript
  await page.waitForTimeout(2000);
  
  console.log('=== CONSOLE LOGS ===');
  logs.forEach(log => console.log(log));
  
  console.log('=== PAGE ERRORS ===');
  errors.forEach(error => console.log(error));
  
  // Check if the alert appeared (indicating JavaScript is running)
  const alertPromise = page.waitForEvent('dialog');
  const hasAlert = await Promise.race([
    alertPromise.then(() => true),
    page.waitForTimeout(1000).then(() => false)
  ]);
  
  console.log('Alert appeared:', hasAlert);
  
  // Check if any JavaScript elements exist
  const jsElements = await page.locator('script').count();
  console.log('Script elements found:', jsElements);
});
