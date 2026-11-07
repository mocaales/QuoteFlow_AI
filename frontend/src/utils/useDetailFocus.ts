import { useEffect, useRef } from 'react';
// Focus the heading when a detail opens; on return, focus the control that opened it (fallback: the list heading).
export default function useDetailFocus(open: boolean) {
 const heading = useRef<HTMLHeadingElement>(null), root = useRef<HTMLElement>(null), opener = useRef(''), was = useRef(false);
 useEffect(() => {
  if (open) { was.current = true; heading.current?.focus(); return; }
  if (!was.current) return;
  was.current = false;
  const target = opener.current ? Array.from(root.current?.querySelectorAll<HTMLElement>('[aria-label]') ?? []).find(el => el.getAttribute('aria-label') === opener.current) : null;
  (target ?? heading.current)?.focus();
 }, [open]);
 return { heading, root, remember: (label: string) => { opener.current = label; } };
}
