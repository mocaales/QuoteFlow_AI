import type { CalculationResult } from './types';

export async function checkHealth(): Promise<void> {
 const response = await fetch('/api/health');
 if (!response.ok) throw new Error('API ni dosegljiv');
}

export async function calculate(payload: Record<string, FormDataEntryValue>): Promise<CalculationResult> {
 const response = await fetch('/api/demo/calculate', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ ...payload, stock: payload.stock === '' ? null : Number(payload.stock), lead_days: payload.lead_days === '' ? null : Number(payload.lead_days) }),
 });
 if (!response.ok) throw new Error(response.status === 422 ? 'Preverite vnesene vrednosti in dovoljeno število decimalk (največ štiri).' : 'Izračun trenutno ni dosegljiv.');
 return response.json();
}
