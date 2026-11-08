import { useCallback, useEffect, useRef } from 'react';

// Marks a horizontally scrolling .tabs element with data-more while content is hidden to the right.
export default function useTabsOverflow() {
 const el = useRef<HTMLDivElement | null>(null), off = useRef<(() => void) | undefined>(undefined);
 const ref = useCallback((node: HTMLDivElement | null) => {
  off.current?.(); off.current = undefined; el.current = node;
  if (!node) return;
  const update = () => { if (node.scrollLeft + node.clientWidth < node.scrollWidth - 1) node.setAttribute('data-more', ''); else node.removeAttribute('data-more'); };
  update(); node.addEventListener('scroll', update); window.addEventListener('resize', update);
  const ro = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(update); ro?.observe(node);
  off.current = () => { node.removeEventListener('scroll', update); window.removeEventListener('resize', update); ro?.disconnect(); };
 }, []);
 useEffect(() => () => off.current?.(), []);
 return ref;
}
