import { useEffect, useState } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import { ApiError } from '../../../services/api';
import { getCustomerInvoice } from '../api';
import type { Invoice } from '../types';
import InvoiceDocument from './InvoiceDocument';

export default function CustomerInvoice({ client, projectId }: { client: SupabaseClient; projectId: string }) {
 const [invoice, setInvoice] = useState<Invoice | null>(null);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState('');
 useEffect(() => {
  let current = true;
  getCustomerInvoice(client, projectId).then(next => { if (current) setInvoice(next); })
   .catch(e => { if (current && !(e instanceof ApiError && e.status === 404)) setError(e instanceof Error ? e.message : 'Računa ni mogoče naložiti.'); })
   .finally(() => { if (current) setLoading(false); });
  return () => { current = false; };
 }, [client, projectId]);
 if (loading) return <div className="loading-state" role="status">Nalagam račun …</div>;
 if (error) return <p role="alert" className="alert">{error}</p>;
 if (!invoice) return <section className="panel"><h2>Račun</h2><p>Račun še ni izdan.</p></section>;
 return <InvoiceDocument invoice={invoice}/>;
}
