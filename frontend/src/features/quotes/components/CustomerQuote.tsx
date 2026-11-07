import { useCallback, useEffect, useRef, useState } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import ActionAlert from '../../../components/ActionAlert';
import Icon from '../../../components/Icon';
import { dateTime, money, percent, quantity } from '../../../utils/format';
import { decideQuote, getCustomerQuotes } from '../api';
import { unitLabels } from '../../../utils/units';
import { stateLabels, type CustomerQuote as Quote } from '../types';

export default function CustomerQuote({ client, projectId }: { client: SupabaseClient; projectId: string }) {
 const [quote, setQuote] = useState<Quote | null>(null);
 const [loading, setLoading] = useState(true);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 const [loadFailed, setLoadFailed] = useState(false);
 const [confirming, setConfirming] = useState<boolean | null>(null);
 const sequence = useRef(0), group = useRef<HTMLDivElement>(null), accept = useRef<HTMLButtonElement>(null), reject = useRef<HTMLButtonElement>(null), outcome = useRef<HTMLDivElement>(null), opener = useRef<boolean | null>(null);
 const [loadError, setLoadError] = useState('');
 const load = useCallback(async () => {
  const request = ++sequence.current;
  try {
   const list = await getCustomerQuotes(client, projectId);
   const latest = list.reduce<Quote | null>((best, item) => !best || item.razlicica > best.razlicica ? item : best, null);
   if (request === sequence.current) { setQuote(latest); setLoadFailed(false); }
  } finally { if (request === sequence.current) setLoading(false); }
 }, [client, projectId]);
 useEffect(() => { void load().catch(e => { setLoadFailed(true); setLoadError(e instanceof Error ? e.message : 'Ponudbe ni mogoče naložiti.'); }); return () => { sequence.current++; }; }, [load]);
 useEffect(() => {
  if (confirming !== null) group.current?.querySelector('button')?.focus();
  else if (opener.current !== null) { (opener.current ? accept : reject).current?.focus(); opener.current = null; }
 }, [confirming]);
 async function decide(approve: boolean) {
  if (!quote) return;
  setBusy(true); setError('');
  try { await decideQuote(client, projectId, quote.id, approve); opener.current = null; setConfirming(null); await load(); outcome.current?.focus(); }
  catch (e) { setError(e instanceof Error ? e.message : 'Odločitve ni mogoče shraniti.'); }
  finally { setBusy(false); }
 }
 const ask = (value: boolean) => { opener.current = value; setConfirming(value); };
 if (loading) return <div className="loading-state" role="status">Nalagam ponudbo …</div>;
 if (loadFailed) return <p role="alert" className="alert">{loadError}</p>;
 if (!quote) return <section className="panel"><h2>Ponudba</h2><p>Podjetje vam še ni poslalo ponudbe.</p></section>;
 const expired = !!quote.velja_do && quote.velja_do < new Date().toISOString().slice(0, 10);
 const open = quote.stanje === 'poslana' && !quote.nadomescena && !expired;
 const note = quote.nadomescena ? 'Ta ponudba je nadomeščena z novejšo različico.' : quote.stanje === 'poslana' && expired ? 'Ponudba je potekla in nanjo ni več mogoče odgovoriti.' : '';
 return <div className="decision-layout">
 <section className="quote-editor" aria-busy={busy}>
  <div className="section-heading"><h2>Ponudba {quote.stevilka}</h2><span className="status-badge">{stateLabels[quote.stanje] ?? quote.stanje}</span></div>
  <p className="muted">Izvajalec: {quote.podjetje_naziv} · Različica {quote.razlicica} · Poslano {dateTime(quote.poslano_ob)}</p>
  <div className="table-wrap"><table className="data-table"><caption className="sr-only">Postavke ponudbe {quote.stevilka}</caption><thead><tr><th>Postavka</th><th className="num">Izmera</th><th className="num">Neto</th><th className="num">DDV</th><th className="num">Končna cena</th></tr></thead><tbody>
   {quote.postavke.map(line => { const unit = unitLabels[line.enota] ?? line.enota; return <tr key={line.zaporedje}><td><strong>{line.naziv}</strong><span className="cell-detail">{[line.vrsta_dela, line.opis].filter(Boolean).join(' · ')}</span>
    {!!line.izmere?.length && <><ul className="measure-list compact" aria-label={`Izmere ${line.naziv}`}>{line.izmere.map(m => { const dims = [m.dolzina, m.visina, m.sirina].filter((x): x is string => x !== null).map(x => quantity(x)).join(' × '); return <li key={m.zaporedje} className="measure-row"><span className="measure-sign">{m.odstej ? '−' : '+'}</span><span className="measure-value">{quantity(m.vrednost)} {unit}</span><span className="measure-dims">{dims}{Number(m.kosi) !== 1 ? `${dims ? ', ' : ''}${quantity(m.kosi)} kosi` : ''}</span></li>; })}</ul>
     <p className="measure-total">Skupaj izmer <strong>{quantity(line.izmera_skupaj)} {unit}</strong></p></>}</td>
    <td className="num">{line.izmera_skupaj ? `${quantity(line.izmera_skupaj)} ${unit}` : '–'}</td><td className="num" data-label="Neto">{money(line.neto)}</td>
    <td className="num" data-label="DDV">{percent(line.stopnja_ddv)}</td><td className="num" data-label="Končna cena">{money(line.koncna_cena)}</td></tr>; })}
  </tbody></table></div>
  <dl className="kpi-strip" role="group" aria-label="Vsote ponudbe"><div><dt>Neto</dt><dd>{money(quote.neto)}</dd></div><div><dt>DDV</dt><dd>{money(quote.ddv)}</dd></div><div><dt>Za plačilo</dt><dd>{money(quote.skupaj)}</dd></div><div><dt>Velja do</dt><dd>{quote.velja_do ? new Date(quote.velja_do).toLocaleDateString('sl-SI') : '—'}</dd></div></dl>
  {quote.ddv_po_stopnjah.length > 0 && <p className="table-footnote">{quote.ddv_po_stopnjah.map(r => `DDV ${percent(r.stopnja_ddv)}: osnova ${money(r.osnova)}, davek ${money(r.ddv)}`).join(' · ')}</p>}
 </section>
 <aside className="panel decision-panel" aria-label="Odločitev">
  <h2>Odločitev</h2>
  <div role="status" tabIndex={-1} ref={outcome} className="decision-outcome">{quote.stanje === 'sprejeta' ? <dl><div><dt>Ponudba je sprejeta</dt><dd>Projekt je v fazi termin. Mojster določi termin izvedbe, osnutek računa je pripravljen.</dd></div></dl> : quote.stanje === 'zavrnjena' ? <dl><div><dt>Ponudba je zavrnjena</dt><dd>Mojster lahko pripravi novo različico ponudbe.</dd></div></dl> : null}</div>
  {quote.stanje === 'poslana' && <dl><div><dt>Po sprejemu</dt><dd>Projekt preide v termin, nastane osnutek računa.</dd></div><div><dt>Po zavrnitvi</dt><dd>Mojster lahko pripravi novo različico ponudbe.</dd></div></dl>}
  <p className="muted">Interni podatki izvajalca so skriti.</p>
  {note && <p className="notice" role="status">{note}</p>}
  {open && (confirming === null
   ? <div className="row-actions"><button type="button" ref={accept} disabled={busy} onClick={() => ask(true)}><Icon name="check"/>Sprejmi ponudbo</button><button type="button" ref={reject} className="secondary" disabled={busy} onClick={() => ask(false)}><Icon name="close"/>Zavrni ponudbo</button></div>
   : <div className="row-actions" role="group" aria-label="Potrditev odločitve" ref={group}><p>{confirming ? 'Ali res želite sprejeti ponudbo?' : 'Ali res želite zavrniti ponudbo?'}</p><button type="button" disabled={busy} onClick={() => void decide(confirming)}><Icon name="check"/>{confirming ? 'Potrdi sprejem' : 'Potrdi zavrnitev'}</button><button type="button" className="secondary" disabled={busy} onClick={() => setConfirming(null)}>Prekliči</button></div>)}
  {error && <ActionAlert>{error}</ActionAlert>}
 </aside>
</div>;
}
