import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
import Icon, { type IconName } from './Icon';

export type MenuEntry = { id: string; label: string; icon?: IconName; onSelect: () => void; disabled?: boolean; reason?: string; danger?: boolean } | { separator: true };
const isItem = (entry: MenuEntry): entry is Exclude<MenuEntry, { separator: true }> => !('separator' in entry);

export default function ActionMenu({ label, items }: { label: string; items: MenuEntry[] }) {
 const id = useId(), [open, setOpen] = useState(false), [pos, setPos] = useState<{ top: number; left: number } | null>(null);
 const trigger = useRef<HTMLButtonElement>(null), menu = useRef<HTMLDivElement>(null), focusAt = useRef<'first' | 'last'>('first');
 const enabled = () => [...menu.current?.querySelectorAll<HTMLElement>('[role=menuitem]:not([aria-disabled=true])') ?? []];
 function show(at: 'first' | 'last') { focusAt.current = at; setOpen(true); }
 useEffect(() => {
  if (!open || !menu.current || !trigger.current) return;
  const rect = trigger.current.getBoundingClientRect(), box = menu.current.getBoundingClientRect(), vw = window.innerWidth, vh = window.innerHeight;
  const below = vh - rect.bottom, top = below < box.height + 8 ? rect.top - 6 - box.height : rect.bottom + 6;
  setPos({ top: Math.max(8, Math.min(top, vh - box.height - 8)), left: Math.max(8, Math.min(rect.right - box.width, vw - box.width - 8)) });
  const outside = (e: Event) => { if (!menu.current?.contains(e.target as Node) && !trigger.current?.contains(e.target as Node)) setOpen(false); };
  const born = performance.now(), dismiss = (e: Event) => { if (e.type === 'scroll' && performance.now() - born < 300) return; setOpen(false); }; // opening itself may scroll the page (focus, tap)
  document.addEventListener('pointerdown', outside, true); window.addEventListener('scroll', dismiss, true); window.addEventListener('resize', dismiss);
  return () => { document.removeEventListener('pointerdown', outside, true); window.removeEventListener('scroll', dismiss, true); window.removeEventListener('resize', dismiss); setPos(null); };
 }, [open]);
 useEffect(() => { if (!open || !pos) return; const list = enabled(); (focusAt.current === 'last' ? list[list.length - 1] : list[0])?.focus({ preventScroll: true }); }, [open, !pos]);
 function select(entry: Exclude<MenuEntry, { separator: true }>) {
  if (entry.disabled) return;
  setOpen(false); trigger.current?.focus(); requestAnimationFrame(entry.onSelect);
 }
 function keys(e: KeyboardEvent) {
  const list = enabled(), at = list.indexOf(document.activeElement as HTMLElement);
  if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); setOpen(false); trigger.current?.focus(); }
  else if (e.key === 'Tab') setOpen(false);
  else if (e.key === 'ArrowDown') { e.preventDefault(); list[(at + 1) % list.length]?.focus(); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); list[(at - 1 + list.length) % list.length]?.focus(); }
  else if (e.key === 'Home') { e.preventDefault(); list[0]?.focus(); }
  else if (e.key === 'End') { e.preventDefault(); list[list.length - 1]?.focus(); }
 }
 return <>
  <button ref={trigger} type="button" className="icon-action more" aria-haspopup="menu" aria-expanded={open} aria-controls={id} aria-label={label} data-tip="Več dejanj"
   onClick={() => open ? setOpen(false) : show('first')} onKeyDown={e => { if (e.key === 'ArrowDown') { e.preventDefault(); show('first'); } else if (e.key === 'ArrowUp') { e.preventDefault(); show('last'); } }}><Icon name="more"/></button>
  {open && <div id={id} ref={menu} role="menu" aria-label={label} className="menu" style={{ position: 'fixed', top: pos?.top ?? 0, left: pos?.left ?? 0, visibility: pos ? 'visible' : 'hidden' }} onKeyDown={keys}>
   {items.map((entry, i) => isItem(entry) ? <button key={entry.id} type="button" role="menuitem" tabIndex={-1} className={`menu-item${entry.danger ? ' danger' : ''}`} aria-disabled={entry.disabled || undefined} onClick={() => select(entry)}>
    {entry.icon && <Icon name={entry.icon}/>}<span>{entry.label}</span>{entry.disabled && entry.reason && <small>{entry.reason}</small>}</button> : <hr key={`s${i}`} role="separator" className="menu-sep"/>)}
  </div>}
 </>;
}
