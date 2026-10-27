import React, { useEffect, useState } from 'react';
import Brand from '../components/Brand';
import { calculate, checkHealth } from '../features/calculator/api';
import type { CalculationResult } from '../features/calculator/types';

const euro = (value: string) => new Intl.NumberFormat('sl-SI', {style: 'currency', currency: 'EUR'}).format(Number(value));
export default function DemoPage() {
 const [status, setStatus] = useState('Preverjam povezavo …');
 const [result, setResult] = useState<CalculationResult | null>(null);
 const [busy, setBusy] = useState(false);
 const [error, setError] = useState('');
 useEffect(() => { checkHealth().then(() => { setStatus('API je dosegljiv'); }).catch(() => setStatus('API ni dosegljiv')); }, []);
 async function submit(event: React.FormEvent<HTMLFormElement>) {
  event.preventDefault(); setBusy(true); setError(''); setResult(null);
  const data = new FormData(event.currentTarget);
  const payload = Object.fromEntries(data.entries());
  try {
   setResult(await calculate(payload));
  } catch (e) { setError(e instanceof Error ? e.message : 'Napaka povezave.'); }
  finally { setBusy(false); }
 }
 return <div className="shell">
  <aside><Brand/><p className="muted">Delovni prostor</p><nav aria-label="Glavna navigacija"><a href="#calculation" aria-current="page">Preverjanje ponudbe <span>↗</span></a></nav><div className="sidebar-bottom">Razvojno ogrodje · 0.1<br/><span>{status}</span></div></aside>
  <main><header><span>Prodajne ponudbe / Kalkulacija</span><span className="tag">Demonstracija</span></header>
   <section className="intro"><p className="eyebrow">PREGLED PRED ODOBRITVIJO</p><h1>Preverite pogoje ponudbe.</h1><p>Izračun cene, marže in odstopanj na enem mestu.</p></section>
   <div className="workspace" id="calculation"><section><h2>Podatki za izračun</h2><p className="muted">Vnesene vrednosti so demonstracijske. Izračun se ne shrani kot ponudba.</p>
   <form onSubmit={submit} onChange={() => setResult(null)}><div className="fields">
    <label>Količina (kos)<input name="quantity" type="number" min="1" max="1000000" step="1" defaultValue="50" required/></label>
    <label>Prodajna cena na kos (€)<input name="unit_price" type="number" min="0.0001" max="100000000" step="0.0001" defaultValue="110" required/></label>
    <label>Neposredni strošek na kos (€)<input name="unit_cost" type="number" min="0" max="100000000" step="0.0001" defaultValue="80" required/></label>
    <label>Popust (delež, 0.1 = 10 %)<input name="discount" type="number" min="0" max="0.9999" step="0.0001" defaultValue="0" required/></label>
    <label>Potrjena zaloga (kos)<input name="stock" type="number" min="0" step="1" defaultValue="50" placeholder="Neznana"/></label>
    <label>Dobavni rok (dni)<input name="lead_days" type="number" min="0" max="3650" step="1" defaultValue="5" placeholder="Neznan"/></label>
    <label>Zahtevani rok (dni)<input name="requested_days" type="number" min="0" max="3650" step="1" defaultValue="7" required/></label>
   </div><p className="policy">Pravila demonstracije: najmanj 20 % marže in največ 10 % popusta. Vsi zneski so brez DDV.</p><button disabled={busy}>{busy ? 'Preverjam …' : 'Izračunaj in preveri'} <span>→</span></button></form>
   </section><section className="result" aria-live="polite" aria-busy={busy}><h2>Rezultat preverjanja</h2>{error && <p role="alert">{error}</p>}{result ? <><p className="total">{euro(result.total)}</p><p className="muted">Skupna prodajna vrednost brez DDV</p><dl><div><dt>Neposredni stroški</dt><dd>{euro(result.cost)}</dd></div><div><dt>Bruto marža</dt><dd>{result.margin === null ? 'Ni določena' : `${(Number(result.margin)*100).toFixed(2)} %`}</dd></div></dl><h3>{result.checks_passed ? 'Preverjanja uspešna' : 'Potrebni so popravki'}</h3>{result.issues.length > 0 && <ul>{result.issues.map(issue => <li key={issue}>{issue}</li>)}</ul>}<p className="muted">To ni odobrena ponudba. Poslovni postopek odobritve še ni vključen.</p></> : <div className="empty"><span aria-hidden="true">↗</span><p>Rezultat bo prikazan<br/>po preverjanju podatkov.</p></div>}</section></div>
   <footer>QuoteFlow AI <span>RFQ → osnutek → pregled → odobrena ponudba</span></footer>
  </main></div>;
}
