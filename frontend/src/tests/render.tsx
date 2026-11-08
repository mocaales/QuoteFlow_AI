/// <reference types="vite/client" />
import type { ReactElement, ReactNode } from 'react';
import { render as rtlRender, waitFor, type RenderOptions } from '@testing-library/react';
import { expect } from 'vitest';

// Falls back to a plain fragment while components/Toaster.tsx does not exist, so tests fail on the missing toast, not on the import.
const found = Object.values(import.meta.glob('../components/Toaster.tsx', { eager: true }))[0] as { default?: (p: { children: ReactNode }) => ReactElement } | undefined;
const Provider = found?.default ?? (({ children }: { children: ReactNode }) => <>{children}</>);

export const render = (ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) => rtlRender(ui, { ...options, wrapper: ({ children }) => <Provider>{children}</Provider> });

// A success message must be a toast in the live region, never an inline notice paragraph.
export async function expectToast(text: string | RegExp) {
 await waitFor(() => {
  const toasts = [...document.querySelectorAll('.toast-region .toast')];
  expect(toasts.some(t => typeof text === 'string' ? (t.textContent ?? '').includes(text) : text.test(t.textContent ?? ''))).toBe(true);
 });
 expect(document.querySelector('p.notice')).toBeNull();
}
