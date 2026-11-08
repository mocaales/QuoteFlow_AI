import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ToastProvider from '../components/Toaster';
import { useToast } from '../lib/toast';

function Fire({ messages }: { messages: string[] }) { const toast = useToast(); return <button onClick={() => messages.forEach(m => toast(m))}>Sproži</button>; }
const show = (...messages: string[]) => { render(<ToastProvider><Fire messages={messages}/></ToastProvider>); return userEvent.setup({ advanceTimers: vi.advanceTimersByTime }); };
const toasts = () => [...document.querySelectorAll('.toast-region .toast')];
// Testing Library only auto-advances fake timers when a global jest exists.
(globalThis as any).jest = { advanceTimersByTime: (ms: number) => vi.advanceTimersByTime(ms) };
beforeEach(() => { vi.useFakeTimers({ shouldAdvanceTime: false }); });
afterEach(() => { vi.useRealTimers(); });

describe('Obvestila (Toaster)', () => {
 it('ena živa regija role=status aria-live=polite je prisotna že brez obvestil', () => {
  show('x'); const region = screen.getByRole('status'); expect(region.className).toContain('toast-region'); expect(region.getAttribute('aria-live')).toBe('polite'); expect(toasts()).toHaveLength(0);
 });
 it('useToast pokaže sporočilo v živi regiji', async () => {
  const user = show('Projekt je ustvarjen.'); await user.click(screen.getByRole('button', { name: 'Sproži' }));
  expect(toasts()).toHaveLength(1); expect(within(screen.getByRole('status')).getByText('Projekt je ustvarjen.')).toBeTruthy();
 });
 it('gumb Zapri obvestilo odstrani obvestilo', async () => {
  const user = show('Shranjeno.'); await user.click(screen.getByRole('button', { name: 'Sproži' }));
  await user.click(screen.getByRole('button', { name: 'Zapri obvestilo' })); expect(toasts()).toHaveLength(0);
 });
 it('obvestilo samo izgine po 5 s, prej ne', async () => {
  const user = show('Shranjeno.'); await user.click(screen.getByRole('button', { name: 'Sproži' }));
  act(() => { vi.advanceTimersByTime(4900); }); expect(toasts()).toHaveLength(1);
  act(() => { vi.advanceTimersByTime(200); }); expect(toasts()).toHaveLength(0);
 });
 it('med lebdenjem se odštevanje ustavi in se po odmiku nadaljuje', async () => {
  const user = show('Shranjeno.'); await user.click(screen.getByRole('button', { name: 'Sproži' }));
  await user.hover(toasts()[0]); act(() => { vi.advanceTimersByTime(20000); }); expect(toasts()).toHaveLength(1);
  await user.unhover(toasts()[0]); act(() => { vi.advanceTimersByTime(5100); }); expect(toasts()).toHaveLength(0);
 });
 it('med fokusom se odštevanje ustavi', async () => {
  const user = show('Shranjeno.'); await user.click(screen.getByRole('button', { name: 'Sproži' }));
  act(() => { screen.getByRole('button', { name: 'Zapri obvestilo' }).focus(); }); act(() => { vi.advanceTimersByTime(20000); }); expect(toasts()).toHaveLength(1);
 });
 it('hkrati so vidna največ tri obvestila, najstarejše odpade', async () => {
  const user = show('Ena', 'Dve', 'Tri', 'Štiri'); await user.click(screen.getByRole('button', { name: 'Sproži' }));
  expect(toasts().map(t => t.textContent)).toEqual([expect.stringContaining('Dve'), expect.stringContaining('Tri'), expect.stringContaining('Štiri')]);
  expect(screen.queryByText('Ena')).toBeNull();
 });
});
