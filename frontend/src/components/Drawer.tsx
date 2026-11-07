import { useEffect, useRef, type ReactNode } from 'react';
import IconButton from './IconButton';
export default function Drawer({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
 const dialog = useRef<HTMLDialogElement>(null);
 useEffect(() => {
  const el = dialog.current!, opener = document.activeElement as HTMLElement | null;
  el.showModal();
  return () => { el.close(); if (opener?.isConnected) opener.focus(); };
 }, []);
 return <dialog ref={dialog} className="drawer" aria-label={title} onCancel={event => { event.preventDefault(); onClose(); }} onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
  <div className="drawer-inner"><div className="drawer-heading"><h2>{title}</h2><IconButton icon="close" label="Zapri" onClick={onClose}/></div>{children}</div>
 </dialog>;
}
