import { useState, type FormEvent, type ReactNode } from 'react';
import Drawer from '../../../components/Drawer';
import Icon from '../../../components/Icon';

// Assign a mojster/delavec role; `pick` renders the single select (user or company), `fixed` is the preselected other side.
export default function RoleDrawer({ title, busy, error, pick, onSubmit, onClose }: { title: string; busy: boolean; error: ReactNode; pick: (role: 'mojster' | 'delavec') => ReactNode; onSubmit: (vloga: 'mojster' | 'delavec', data: FormData) => void; onClose: () => void }) {
 const [role, setRole] = useState<'mojster' | 'delavec'>('delavec');
 function submit(e: FormEvent<HTMLFormElement>) { e.preventDefault(); onSubmit(role, new FormData(e.currentTarget)); }
 return <Drawer title={title} onClose={onClose}>
  {error}
  <form className="editor-form" onSubmit={submit}>
   {pick(role)}
   <fieldset><legend>Vloga</legend>
    <label><input type="radio" name="vloga" value="delavec" checked={role === 'delavec'} onChange={() => setRole('delavec')}/> Delavec</label>
    <label><input type="radio" name="vloga" value="mojster" checked={role === 'mojster'} onChange={() => setRole('mojster')}/> Mojster</label>
    <p className="muted">Mojster lahko upravlja cenik, projekte in delavce podjetja.</p>
   </fieldset>
   <div className="row-actions"><button type="button" className="secondary" onClick={onClose}><Icon name="close"/>Prekliči</button><button disabled={busy}><Icon name="user-plus"/>Dodeli vlogo</button></div>
  </form>
 </Drawer>;
}
