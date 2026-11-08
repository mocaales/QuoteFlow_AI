import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { ToastContext } from '../lib/toast';
import Icon from './Icon';

type Item = { id: number; message: string; leaving: boolean };
const canPopover = typeof HTMLElement !== 'undefined' && 'showPopover' in HTMLElement.prototype; // jsdom styles an unshown popover as display:none
const LIFETIME = 5000, LEAVE = 160, MAX = 3;

function Toast({ item, onClose }: { item: Item; onClose: (id: number) => void }) {
 const [leaving, setLeaving] = useState(false);
 const remaining = useRef(LIFETIME), started = useRef(0), timers = useRef<number[]>([]);
 const stop = useCallback((pause: boolean) => {
  timers.current.forEach(window.clearTimeout); timers.current = [];
  if (pause) { remaining.current = Math.max(remaining.current - (Date.now() - started.current), LEAVE + 1); setLeaving(false); }
 }, []);
 const start = useCallback(() => {
  started.current = Date.now();
  // The fade-out runs inside the 5 s so removal happens exactly at the end.
  timers.current = [window.setTimeout(() => setLeaving(true), remaining.current - LEAVE), window.setTimeout(() => onClose(item.id), remaining.current)];
 }, [item.id, onClose]);
 useEffect(() => { start(); return () => stop(false); }, [start, stop]);
 return <div className={`toast${leaving ? ' leaving' : ''}`} onMouseEnter={() => stop(true)} onMouseLeave={() => { stop(false); start(); }} onFocus={() => stop(true)} onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget)) { stop(false); start(); } }}>
  <span className="toast-icon"><Icon name="check-circle"/></span><span className="toast-text">{item.message}</span>
  <button type="button" className="icon-action toast-close" aria-label="Zapri obvestilo" data-tip="Zapri" onClick={() => onClose(item.id)}><Icon name="close"/></button>
 </div>;
}

export default function ToastProvider({ children }: { children: ReactNode }) {
 const [items, setItems] = useState<Item[]>([]);
 const region = useRef<HTMLDivElement>(null), next = useRef(0);
 useEffect(() => { try { region.current?.showPopover?.(); } catch { /* not supported */ } }, []);
 const close = useCallback((id: number) => setItems(list => list.filter(item => item.id !== id)), []);
 const toast = useCallback((message: string) => {
  setItems(list => [...list, { id: ++next.current, message, leaving: false }].slice(-MAX));
  // A modal dialog hides everything outside the top layer order; re-promote the region above it.
  if (document.querySelector('dialog[open]')) try { region.current?.hidePopover?.(); region.current?.showPopover?.(); } catch { /* not supported */ }
 }, []);
 return <ToastContext.Provider value={toast}>{children}
  <div className="toast-region" role="status" aria-live="polite" popover={canPopover ? 'manual' : undefined} ref={region}>{items.map(item => <Toast key={item.id} item={item} onClose={close}/>)}</div>
 </ToastContext.Provider>;
}
