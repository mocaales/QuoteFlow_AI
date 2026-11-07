import { useState } from 'react';
import Icon from '../../../components/Icon';
import type { AdminRole } from '../types';
import { roleNames } from '../types';

// Revoke asks first (inline), restore is immediate. `protectedNote` disables revoke with a visible reason.
export default function RoleAction({ role, busy, protectedNote, onChange }: { role: AdminRole; busy: boolean; protectedNote?: string; onChange: (active: boolean, message: string) => void }) {
 const [confirming, setConfirming] = useState(false);
 const who = `${roleNames[role.vloga]} uporabniku ${role.e_posta}`;
 if (role.vloga === 'admin') return null;
 if (!role.aktivna) return <button type="button" className="secondary small" aria-label={`Ponovno aktiviraj vlogo ${who}`} disabled={busy} onClick={() => onChange(true, 'Vloga je ponovno aktivna.')}><Icon name="restore"/>Ponovno aktiviraj</button>;
 if (protectedNote) return <><button type="button" className="secondary small" aria-label={`Odvzemi vlogo ${who}`} aria-describedby={`note-${role.id}`} disabled><Icon name="lock"/>Odvzemi</button><span id={`note-${role.id}`} className="owner-note">{protectedNote}</span></>;
 if (confirming) return <div className="row-confirm"><p>{`Odvzamem vlogo ${who} pri podjetju ${role.naziv ?? ''}?`}</p>
  <button type="button" className="secondary small" disabled={busy} onClick={() => { setConfirming(false); onChange(false, 'Vloga je odvzeta.'); }}><Icon name="revoke"/>Odvzemi vlogo</button>
  <button type="button" className="secondary small" onClick={() => setConfirming(false)}><Icon name="close"/>Prekliči</button></div>;
 return <button type="button" className="secondary small" aria-label={`Odvzemi vlogo ${who}`} disabled={busy} onClick={() => setConfirming(true)}><Icon name="revoke"/>Odvzemi</button>;
}
