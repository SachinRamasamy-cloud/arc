/** Browser qualification requires local portal/API servers and a seeded development account. */
import {test,expect} from '@playwright/test';

test('the portal developer guide works without a signed-in session',async({page})=>{
 await page.goto('http://127.0.0.1:5173/docs');
 await expect(page.getByRole('heading',{name:'Connect an API in minutes.'})).toBeVisible();
 await page.getByRole('searchbox',{name:'Search the API guide'}).fill('webhooks');
 await expect(page.getByRole('heading',{name:'SSE and webhooks'})).toBeVisible();
 await expect(page.locator('body')).not.toContainText('Traceback');
});

test('public backend docs reveal only the public API schema',async({request})=>{
 const response=await request.get('http://127.0.0.1:8000/docs');
 expect(response.status()).toBe(200);
 const body=await response.text();
 expect(body).toContain('/v1/jobs');
 expect(body).not.toContain('/api/operator/');
 expect(body).not.toContain('sk_live_');
});

test('team page does not show an empty table while members are loading',async({page})=>{
 const base='**/api/console/v1';
 await page.route(base+'/auth/me',route=>route.fulfill({json:{user:{id:'usr_1',name:'Test Owner',email:'owner@example.test',preferences:{}}}}));
 await page.route(base+'/workspaces',route=>route.fulfill({json:{items:[{id:'ws_1',name:'Sample Workspace',status:'active',role:'owner'}]}}));
 await page.route(base+'/workspaces/ws_1/projects',route=>route.fulfill({json:{items:[{id:'pr_1',name:'Demo project',archived:false}]}}));
 await page.route(base+'/workspaces/ws_1/members',async route=>{
  await new Promise(resolve=>setTimeout(resolve,450));
  await route.fulfill({json:{items:[{id:'mem_1',user_id:'usr_1',name:'Test Owner',email:'owner@example.test',role:'owner'}],invites:[],can_manage:true}});
 });
 await page.goto('http://127.0.0.1:5173/w/ws_1/team');
 await expect(page.getByText('Loading team members')).toBeVisible();
 await expect(page.getByText('No members.')).toHaveCount(0);
 await expect(page.getByText('owner@example.test')).toBeVisible();
 await expect(page.getByText('Loading team members')).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Invite teammate'})).toBeVisible();
});
