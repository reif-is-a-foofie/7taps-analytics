import { test, expect } from '@playwright/test';

test('debug JavaScript execution', async ({ page }) => {
  await page.goto('file:///Users/reif/Documents/POL/7taps-analytics/test_dashboard.html');
  
  // Wait for page to load
  await page.waitForLoadState('networkidle');
  
  // Check if JavaScript status indicator appears
  const jsIndicator = page.locator('#js-status');
  await expect(jsIndicator).toBeVisible({ timeout: 10000 });
  
  // Check console logs
  const logs: string[] = [];
  page.on('console', msg => logs.push(msg.text()));
  
  // Click a sidebar item
  await page.click('text=Data Explorer');
  
  // Wait a moment
  await page.waitForTimeout(2000);
  
  // Check if the indicator updated
  await expect(jsIndicator).toContainText('explorer');
  
  console.log('Console logs:', logs);
});
