export const money = (value: string) => new Intl.NumberFormat('sl-SI', { style: 'currency', currency: 'EUR', maximumFractionDigits: 4 }).format(Number(value));
export const quantity = (value: string) => new Intl.NumberFormat('sl-SI', { maximumFractionDigits: 4 }).format(Number(value));
export const dateTime = (value: string | null) => value ? new Intl.DateTimeFormat('sl-SI', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—';
export const percent = (value: string) => new Intl.NumberFormat('sl-SI', { style: 'percent', maximumFractionDigits: 4 }).format(Number(value));
