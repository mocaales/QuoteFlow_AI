import { useEffect, useState } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import Icon from '../../../components/Icon';
import { dateTime } from '../../../utils/format';
import { getOwnProjects } from '../api';
import { phases, type OwnProject } from '../types';

export default function MyProjects({ client }: { client: SupabaseClient }) {
 const [projects, setProjects] = useState<OwnProject[]>([]);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState('');
 useEffect(() => {
  let current = true;
  getOwnProjects(client).then(next => { if (current) setProjects(next); }).catch(e => { if (current) setError(e instanceof Error ? e.message : 'Projektov ni mogoče naložiti.'); }).finally(() => { if (current) setLoading(false); });
  return () => { current = false; };
 }, [client]);
 return <section className="supplier-view" aria-busy={loading}>
  <div className="page-title"><div><h1>Moji projekti</h1><p>Projekti, ki so jih zanje ustvarila podjetja. Prikaz je samo za branje.</p></div></div>
  {error && <p role="alert" className="alert">{error}</p>}
  {loading ? <div className="loading-state" role="status">Nalagam projekte …</div> : !projects.length && !error ? <div className="full-empty"><Icon name="list"/><h2>Še nimate projektov</h2><p>Projekt se prikaže, ko ga za vas ustvari mojster.</p></div> : !!projects.length && <div className="table-wrap"><table className="data-table"><caption className="sr-only">Moji projekti</caption><thead><tr><th>Projekt</th><th>Faza</th><th>Podjetje</th><th className="num">Termin</th></tr></thead><tbody>
   {projects.map(project => <tr key={project.id}><td><strong>{project.naziv}</strong><span className="cell-detail">{project.lokacija_izvedbe}</span></td>
    <td><span className="status-badge confirmed">{phases.find(([id]) => id === project.faza)?.[1] ?? project.faza}</span></td>
    <td data-label="Podjetje">{project.podjetje_naziv}</td>
    <td className="num" data-label="Termin">{project.termin_od ? `${dateTime(project.termin_od)} – ${dateTime(project.termin_do)}` : '—'}</td></tr>)}
  </tbody></table></div>}
 </section>;
}
