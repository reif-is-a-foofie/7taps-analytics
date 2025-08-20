import { test, expect } from '@playwright/test';

test.describe('Dashboard UI Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('dashboard loads with real data', async ({ page }) => {
    // Check that the dashboard loads
    await expect(page.locator('h1')).toContainText('7taps HR Analytics Explorer');
    
    // Check that real data is displayed (not mock data)
    await expect(page.locator('#total-participants')).toContainText('21');
    
    // Check that completion rate is calculated from real data
    const completionRate = await page.locator('#completion-rate').textContent();
    expect(completionRate).toMatch(/\d+%/);
    expect(completionRate).not.toBe('78%'); // Should not be the old mock value
    
    // Check that insights show real data
    await expect(page.locator('text=Total participants: 21')).toBeVisible();
    await expect(page.locator('text=Total lessons completed:')).toBeVisible();
  });

  test('sidebar navigation works', async ({ page }) => {
    // Test Data Explorer link
    await page.click('text=Data Explorer');
    await expect(page.locator('#explorer')).toBeVisible();
    await expect(page.locator('#dashboard')).not.toBeVisible();
    
    // Test AI Chat link
    await page.click('text=AI Chat');
    await expect(page.locator('#chat')).toBeVisible();
    await expect(page.locator('#explorer')).not.toBeVisible();
    
    // Test Health Check link
    await page.click('text=Health Check');
    await expect(page.locator('#health')).toBeVisible();
    await expect(page.locator('#chat')).not.toBeVisible();
    
    // Test Dashboard link (back to main)
    await page.click('text=Dashboard');
    await expect(page.locator('#dashboard')).toBeVisible();
    await expect(page.locator('#health')).not.toBeVisible();
  });

  test('API docs link opens in new tab', async ({ page, context }) => {
    // Click API Docs link
    const [newPage] = await Promise.all([
      context.waitForEvent('page'),
      page.click('text=API Docs')
    ]);
    
    // Check that new page opened
    expect(newPage.url()).toContain('/docs');
    await expect(newPage.locator('title')).toContainText('Swagger UI');
  });

  test('charts are rendered with real data', async ({ page }) => {
    // Wait for charts to load
    await page.waitForTimeout(2000);
    
    // Check that chart containers exist and have content
    const funnelChart = page.locator('#completion-funnel-chart');
    await expect(funnelChart).toBeVisible();
    
    // Check that chart has SVG elements (indicating it rendered)
    await expect(funnelChart.locator('svg')).toBeVisible();
    
    // Check other charts
    const dropoffChart = page.locator('#dropoff-chart');
    await expect(dropoffChart).toBeVisible();
    await expect(dropoffChart.locator('svg')).toBeVisible();
    
    const knowledgeChart = page.locator('#knowledge-lift-chart');
    await expect(knowledgeChart).toBeVisible();
    await expect(knowledgeChart.locator('svg')).toBeVisible();
    
    const quizChart = page.locator('#quiz-performance-chart');
    await expect(quizChart).toBeVisible();
    await expect(quizChart.locator('svg')).toBeVisible();
  });

  test('data explorer filtering works', async ({ page }) => {
    // Navigate to Data Explorer
    await page.click('text=Data Explorer');
    await expect(page.locator('#explorer')).toBeVisible();
    
    // Select a table
    await page.selectOption('#data-table-select', 'user_responses');
    await page.waitForTimeout(1000);
    
    // Check that data loads
    await expect(page.locator('#data-table')).not.toContainText('Select a data view to begin exploring');
    
    // Test lesson filtering
    await page.selectOption('#lesson-filter', '1');
    await page.waitForTimeout(500);
    
    // Check that filter status shows
    await expect(page.locator('#filter-status')).toContainText('Filtered by lesson');
  });

  test('AI chat functionality works', async ({ page }) => {
    // Navigate to AI Chat
    await page.click('text=AI Chat');
    await expect(page.locator('#chat')).toBeVisible();
    
    // Test quick question button
    await page.click('text=Course Completion');
    await page.waitForTimeout(1000);
    
    // Check that AI response appears
    await expect(page.locator('#chat-messages')).toContainText('AI Assistant:');
    
    // Test manual chat input
    await page.fill('#chat-input', 'How many users completed the course?');
    await page.click('text=Send Message');
    await page.waitForTimeout(1000);
    
    // Check for AI response
    await expect(page.locator('#chat-messages')).toContainText('21 users');
  });

  test('health check shows system status', async ({ page }) => {
    // Navigate to Health Check
    await page.click('text=Health Check');
    await expect(page.locator('#health')).toBeVisible();
    
    // Check that health status loads
    await expect(page.locator('text=System Status: healthy')).toBeVisible();
    await expect(page.locator('text=Connected to PostgreSQL')).toBeVisible();
  });

  test('no mock data is displayed', async ({ page }) => {
    // Check that old mock insights are not present
    await expect(page.locator('text=65% of learners use mobile devices')).not.toBeVisible();
    await expect(page.locator('text=25% reduction in screen time')).not.toBeVisible();
    await expect(page.locator('text=92% click-through rate on quizzes')).not.toBeVisible();
    
    // Check that real insights are present
    await expect(page.locator('text=Total participants: 21')).toBeVisible();
    await expect(page.locator('text=Total lessons completed:')).toBeVisible();
  });

  test('metric cards show calculated values', async ({ page }) => {
    // Check that metrics are calculated from real data
    const totalLearners = await page.locator('#total-participants').textContent();
    expect(totalLearners).toBe('21');
    
    const completionRate = await page.locator('#completion-rate').textContent();
    expect(completionRate).toMatch(/\d+\.\d+%/);
    
    const avgEngagement = await page.locator('#avg-score').textContent();
    expect(avgEngagement).toMatch(/\d+\.\d+/);
    
    const totalLessons = await page.locator('#nps-score').textContent();
    expect(totalLessons).toBe('10');
  });
});
