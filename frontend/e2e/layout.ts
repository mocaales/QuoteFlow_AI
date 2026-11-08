import type { Page } from '@playwright/test';

// Generic layout guarantees for any screen state: no sideways scroll, every control reachable by pointer,
// WCAG 2.5.8 target size, no clipped text. Returns human-readable problems (empty = fine).
export async function layoutProblems(page: Page): Promise<string[]> {
 const isPhone = (page.viewportSize()?.width ?? 1440) < 800;
 return page.evaluate(({ isPhone }) => {
  const problems: string[] = [];
  const visible = (el: Element) => { const r = el.getBoundingClientRect(); return r.width > 1 && r.height > 1 && el.checkVisibility({ opacityProperty: true, visibilityProperty: true }) && !el.closest('[aria-hidden="true"], .sr-only, [inert]'); };
  const name = (el: Element) => `<${el.tagName.toLowerCase()}${el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).join('.') : ''}> "${(el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 40)}"`;

  if (document.documentElement.scrollWidth > document.documentElement.clientWidth + 1) problems.push(`[scroll] page scrolls sideways: ${document.documentElement.scrollWidth}px > ${document.documentElement.clientWidth}px`);

  const controls = [...document.querySelectorAll('button, a[href], [role=tab], [role=menuitem], input:not([type=hidden]), select')].filter(el => visible(el) && !(el as HTMLButtonElement).disabled && el.getAttribute('aria-disabled') !== 'true');
  const modal = document.querySelector('dialog[open]');
  for (const el of controls) {
   if (modal && !modal.contains(el)) continue; // background is inert behind an open dialog
   // Controls inside a scroll container may sit outside the viewport; scroll them in before hit-testing.
   el.scrollIntoView({ block: 'center', inline: 'center' });
   const r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
   if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) { problems.push(`[offscreen] ${name(el)} centre is outside the viewport`); continue; }
   const hit = document.elementFromPoint(x, y);
   // A label wrapping a checkbox/radio/input legitimately receives the click for it.
   const ok = hit && (el === hit || el.contains(hit) || hit.contains(el) && hit.tagName === 'LABEL');
   if (!ok) problems.push(`[covered] ${name(el)} is covered by ${hit ? name(hit) : 'nothing'}`);
  }
  window.scrollTo(0, 0);

  const inText = (el: Element) => !!el.closest('p, li, dd, td, .table-footnote') && getComputedStyle(el).display === 'inline';
  for (const el of document.querySelectorAll('button, a[href], [role=tab]')) {
   if (!visible(el) || (el as HTMLButtonElement).disabled || inText(el)) continue;
   const r = el.getBoundingClientRect();
   if (r.width < 24 - 0.5 || r.height < 24 - 0.5) problems.push(`[target] ${name(el)} is ${r.width.toFixed(0)}x${r.height.toFixed(0)}px (min 24x24)`);
  }

  for (const el of document.querySelectorAll('button, [role=tab], th, .badge, .tag, .pill, .status, [class*=badge]')) {
   if (!visible(el) || el.scrollWidth <= el.clientWidth + 1) continue;
   const ellipsis = getComputedStyle(el).textOverflow === 'ellipsis';
   const full = (el.getAttribute('title') || el.getAttribute('aria-label') || el.getAttribute('data-tip') || '').trim();
   const text = (el.textContent ?? '').trim();
   if (!(ellipsis && (full === text || full.includes(text)))) problems.push(`[clipped] ${name(el)} content ${el.scrollWidth}px in ${el.clientWidth}px${ellipsis ? ' (ellipsis without full-text title)' : ''}`);
  }

  // R3: 44px targets on phone for buttons, tabs, selects, inputs, menuitems (checkbox/radio and inline links exempt).
  if (isPhone) for (const el of document.querySelectorAll('button, [role=tab], [role=menuitem], select, input:not([type=checkbox]):not([type=radio]):not([type=hidden])')) {
   if (!visible(el) || (el as HTMLButtonElement).disabled || inText(el)) continue;
   const r = el.getBoundingClientRect();
   if (r.height < 44 - 0.5 || (r.width < 44 - 0.5 && !(el as HTMLInputElement).type?.startsWith('text'))) problems.push(`[target44] ${name(el)} is ${r.width.toFixed(0)}x${r.height.toFixed(0)}px on phone (min 44)`);
   if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName) && parseFloat(getComputedStyle(el).fontSize) < 16) problems.push(`[font16] ${name(el)} font ${getComputedStyle(el).fontSize} on phone (min 16px, iOS zoom)`);
  }
  // R5: no ellipsis truncation at all, only the sidebar account e-mail may truncate and then carries a title.
  for (const el of document.querySelectorAll('*')) {
   if (!visible(el) || getComputedStyle(el).textOverflow !== 'ellipsis' || el.scrollWidth <= el.clientWidth + 1) continue;
   if (el.closest('.account') && el.getAttribute('title')) continue;
   problems.push(`[ellipsis] ${name(el)} truncated (${el.scrollWidth}px in ${el.clientWidth}px)`);
  }
  for (const el of document.querySelectorAll('td, label, h1, h2, h3, .status-badge, .toast-text')) {
   if (visible(el) && el.scrollWidth > el.clientWidth + 1 && !el.closest('.table-wrap, [tabindex]')) problems.push(`[overflow] ${name(el)} content ${el.scrollWidth}px in ${el.clientWidth}px`);
  }
  return [...new Set(problems)];
 }, { isPhone });
}

// Projekti row actions live in the "Več dejanj <projekt>" menu (mojster workspace).
export async function rowAction(page: Page, projekt: string, akcija: string) {
 await page.getByRole('button', { name: `Več dejanj ${projekt}` }).click();
 await page.getByRole('menuitem', { name: akcija, exact: true }).click();
}
