import { test, expect } from '@playwright/test';

test('debug Heroku JavaScript issues', async ({ page }) => {
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
  
  await page.goto('https://seventaps-analytics-5135b3a0701a.herokuapp.com/');
  await page.waitForLoadState('networkidle');
  
  // Wait a moment for any delayed JavaScript
  await page.waitForTimeout(3000);
  
  console.log('=== CONSOLE LOGS ===');
  logs.forEach(log => console.log(log));
  
  console.log('=== PAGE ERRORS ===');
  errors.forEach(error => console.log(error));
  
  // Check if any JavaScript elements exist
  const jsElements = await page.locator('script').count();
  console.log('Script elements found:', jsElements);
  
  // Try to click a sidebar item and see what happens
  try {
    await page.click('text=Data Explorer');
    console.log('Successfully clicked Data Explorer');
    
    // Wait a moment
    await page.waitForTimeout(2000);
    
    // Check if the section became visible
    const explorerSection = page.locator('#explorer');
    const isVisible = await explorerSection.isVisible();
    console.log('Explorer section visible:', isVisible);
    
  } catch (error) {
    console.log('Error clicking Data Explorer:', error);
  }
});
