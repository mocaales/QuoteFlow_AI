import { useEffect } from 'react';
// WCAG 1.4.13: Escape dismisses the icon tooltip while it is focused or hovered; it returns on blur, leave or refocus.
const TIP = '.icon-action[data-tip]';
export default function useTipEscape() {
 useEffect(() => {
  const tip = (t: EventTarget | null) => t instanceof Element ? t.closest(TIP) : null;
  const show = (e: Event) => tip(e.target)?.removeAttribute('data-tip-hidden');
  const keydown = (e: KeyboardEvent) => {
   if (e.key !== 'Escape') return;
   const active = tip(document.activeElement);
   const hovered = Array.from(document.querySelectorAll(TIP)).find(el => el.matches(':hover'));
   (active ?? hovered)?.setAttribute('data-tip-hidden', '');
  };
  document.addEventListener('keydown', keydown);
  for (const t of ['focusout', 'focusin', 'mouseleave']) document.addEventListener(t, show, true);
  return () => { document.removeEventListener('keydown', keydown); for (const t of ['focusout', 'focusin', 'mouseleave']) document.removeEventListener(t, show, true); };
 }, []);
}
