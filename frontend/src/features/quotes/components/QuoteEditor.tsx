import { useCallback, useEffect, useRef, useState } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import ActionAlert from '../../../components/ActionAlert';
import Icon from '../../../components/Icon';
import { money, percent, quantity } from '../../../utils/format';
import { createQuote, getQuote, getQuotes, sendQuote } from '../api';
import { unitLabels } from '../../../utils/units';
import { stateLabels, type Quote } from '../types';

export default function QuoteEditor({ client, companyId, projectId, onEditItems }: { client: SupabaseClient; companyId: string; projectId: string; onEditItems?: () => void }) {
 const [quote, setQuote] = useState<Quote | null>(null);
 const [loading, setLoading] = useState(true);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const [loadFailed, setLoadFailed] = useState(false);
 const [confirming, setConfirming] = useState(false);
 const group = useRef<HTMLDivElement>(null), sendButton = useRef<HTMLButtonElement>(null), asked = useRef(false);
 const sequence = useRef(0), heading = useRef<HTMLHeadingElement>(null);
 const load = useCallback(async () => {
  const request = ++sequence.current;
  try {
   const list = await getQuotes(client, companyId, projectId);
   // An accepted version is the binding one, even if a newer draft exists.
   const rank = (item: (typeof list)[number]) => (item.stanje === 'sprejeta' ? 1e6 : 0) + item.razlicica;
   const latest = list.reduce<(typeof list)[number] | null>((best, item) => !best || rank(item) > rank(best) ? item : best, null);
   const next = latest ? await getQuote(client, companyId, projectId, latest.id) : null;
   if (request === sequence.current) { setQuote(next); setLoadFailed(false); }
  } finally { if (request === sequence.current) setLoading(false); }
 }, [client, companyId, projectId]);
 useEffect(() => { void load().catch(e => { setLoadFailed(true); setError(e instanceof Error ? e.message : 'Ponudbe ni mogoče naložiti.'); }); return () => { sequence.current++; }; }, [load]);
 async function mutate(action: () => Promise<unknown>) {
  setBusy(true); setError('');
  try { await action(); await load(); heading.current?.focus(); return true; }
  catch (e) { setError(e instanceof Error ? e.message : 'Spremembe ni mogoče shraniti.'); return false; }
  finally { setBusy(false); }
 }
 useEffect(() => {
  if (confirming) { asked.current = true; group.current?.querySelector('button')?.focus(); }
  else if (asked.current) { asked.current = false; sendButton.current?.focus(); }
 }, [confirming]);
 async function send() { await mutate(() => sendQuote(client, companyId, projectId, quote!.id)); setConfirming(false); }
 const alert = error && <ActionAlert>{error}</ActionAlert>;
 if (loading) return <div className="loading-state" role="status">Nalagam ponudbo …</div>;
 if (loadFailed) return alert;
 if (!quote) return <section className="panel">{alert}<h2>Ponudba</h2><p>Projekt še nima ponudbe. Najprej dodajte postavke z izmerami, nato pripravite osnutek.</p>
  <button type="button" disabled={busy} onClick={() => void mutate(() => createQuote(client, companyId, projectId))}><Icon name="plus"/>Ustvari osnutek ponudbe</button></section>;
 const draft = quote.stanje === 'osnutek', empty = !quote.postavke.length;
 return <section className="quote-editor" aria-busy={busy}>
  <div className="section-heading"><h2 tabIndex={-1} ref={heading}>Ponudba {quote.stevilka}</h2><span className="status-badge">{stateLabels[quote.stanje] ?? quote.stanje}</span></div>
  <p className="muted">Različica {quote.razlicica}</p>
  {draft && onEditItems && <div className="row-actions"><button type="button" className="secondary" disabled={busy} onClick={onEditItems}><Icon name="ruler"/>Uredi postavke</button></div>}
  {empty ? <div className="empty-state"><p>Ponudba še nima postavk.</p></div> : <div className="table-wrap"><table className="data-table"><caption className="sr-only">Postavke ponudbe {quote.stevilka}</caption><thead><tr><th>Postavka</th><th className="num">Izmera</th><th className="num">Neto</th><th className="num">DDV</th><th className="num">Končna cena</th></tr></thead><tbody>
   {quote.postavke.map(line => <tr key={line.id}><td><strong>{line.naziv}</strong><span className="cell-detail">{[line.vrsta_dela, line.opis].filter(Boolean).join(' · ')}</span></td>
    <td className="num">{line.izmera_skupaj ? `${quantity(line.izmera_skupaj)} ${unitLabels[line.enota] ?? line.enota}` : '–'}</td><td className="num" data-label="Neto">{money(line.neto)}</td>
    <td className="num" data-label="DDV">{percent(line.stopnja_ddv)}</td><td className="num" data-label="Končna cena">{money(line.koncna_cena)}</td></tr>)}
  </tbody></table></div>}
  <dl className="kpi-strip" role="group" aria-label="Vsote ponudbe"><div><dt>Neto</dt><dd>{money(quote.neto)}</dd></div><div><dt>DDV</dt><dd>{money(quote.ddv)}</dd></div><div><dt>Skupaj</dt><dd>{money(quote.skupaj)}</dd></div><div><dt>Velja do</dt><dd>{quote.velja_do ? new Date(quote.velja_do).toLocaleDateString('sl-SI') : '—'}</dd></div></dl>
  {quote.ddv_po_stopnjah.length > 0 && <p className="table-footnote">{quote.ddv_po_stopnjah.map(r => `DDV ${percent(r.stopnja_ddv)}: osnova ${money(r.osnova)}, davek ${money(r.ddv)}`).join(' · ')}</p>}
  {alert}
  {draft && (confirming
   ? <div className="row-actions" role="group" aria-label="Potrditev pošiljanja" ref={group} onKeyDown={e => { if (e.key === 'Escape' && !busy) setConfirming(false); }}><p>Po pošiljanju ponudbe ne bo več mogoče spreminjati. Za spremembe pripravite novo različico.</p><button type="button" disabled={busy} onClick={() => void send()}><Icon name="check"/>Potrdi pošiljanje</button><button type="button" className="secondary" disabled={busy} onClick={() => setConfirming(false)}>Prekliči</button></div>
   : <div className="row-actions"><button type="button" ref={sendButton} disabled={busy || empty} onClick={() => setConfirming(true)}><Icon name="arrow"/>Pošlji stranki</button>{empty && <p className="field-help">Dodajte postavke z izmerami v Postavke projekta.</p>}</div>)}
  {!draft && (quote.stanje === 'poslana' || quote.stanje === 'zavrnjena') && !quote.nadomescena && <div className="row-actions"><button type="button" className="secondary" disabled={busy} onClick={() => void mutate(() => createQuote(client, companyId, projectId))}><Icon name="refresh"/>Pripravi novo različico</button></div>}
 </section>;
}
