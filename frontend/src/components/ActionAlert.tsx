import { useEffect, useRef } from 'react';
// Error beside the action that failed; scrolls into view so it is not hidden under the sticky header.
export default function ActionAlert({ children }: { children: string }) {
 const el = useRef<HTMLParagraphElement>(null);
 useEffect(() => { el.current?.scrollIntoView?.({ block: 'nearest' }); }, [children]);
 return <p ref={el} role="alert" className="alert">{children}</p>;
}
