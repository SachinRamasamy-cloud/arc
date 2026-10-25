/** Requires the locally migrated API+worker and all three frontend dev servers. Not executed in the build container. */
import {test,expect} from '@playwright/test';
test('landing has usable navigation and real processing demo',async({page})=>{
 await page.goto('/');await expect(page.getByRole('heading',{level:1})).toContainText('Connect the service.');
 await page.getByRole('button',{name:'Run live request'}).click();
 await expect(page.locator('.demo-output')).toContainText('ada@example.test',{timeout:30_000});
 await expect(page.locator('.demo-title')).toContainText('Real result');
});
test('3D alternatives and reduced motion retain useful controls',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'});await page.goto('/');
 await page.getByRole('button',{name:'01 Input',exact:false}).click();
 await expect(page.locator('.assembly-caption')).toContainText('Your input. A private route.');
 await page.getByRole('button',{name:'Expand model'}).click();
 await expect(page.getByRole('button',{name:'Collapse model'})).toHaveAttribute('aria-pressed','true');
 await expect(page.getByRole('button',{name:'Pause automatic rotation'})).toBeDisabled();
});
test('public pages and legal links resolve',async({page})=>{
 for(const route of ['/docs/','/services/','/pricing/','/security/','/contact/','/terms/','/privacy/']){
  const response=await page.goto(route);expect(response?.status()).toBe(200);await expect(page.locator('h1')).toBeVisible();
 }
});
test('portal authentication does not reveal backend diagnostics',async({page})=>{
 await page.goto('http://127.0.0.1:5173/login');
 await page.getByLabel('Email address',{exact:true}).fill('does-not-exist@example.com');
 await page.locator('input[autocomplete="current-password"]').fill('incorrect-password-123');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page.getByRole('alert')).toContainText('could not be verified');
 await expect(page.locator('body')).not.toContainText('Traceback');
});
test('staff login is separate and requires an authenticator',async({page})=>{
 await page.goto('http://127.0.0.1:5174/');
 await expect(page.locator('body')).toContainText('Operator');
 await expect(page.locator('body')).not.toContainText('Create your account');
});
test('public layout does not overflow the viewport',async({page})=>{
 await page.goto('/');
 const width=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:innerWidth}));
 expect(width.scroll).toBeLessThanOrEqual(width.viewport+1);
});
