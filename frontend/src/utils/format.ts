export const money = (value: string) => new Intl.NumberFormat('sl-SI', { style: 'currency', currency: 'EUR', maximumFractionDigits: 4 }).format(Number(value));
export const quantity = (value: string) => new Intl.NumberFormat('sl-SI', { maximumFractionDigits: 4 }).format(Number(value));
export const dateTime = (value: string | null) => value ? new Intl.DateTimeFormat('sl-SI', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—';
export const percent = (value: string) => new Intl.NumberFormat('sl-SI', { style: 'percent', maximumFractionDigits: 4 }).format(Number(value));
export const date = (value: string | null) => value ? new Intl.DateTimeFormat('sl-SI', { dateStyle: 'medium' }).format(new Date(value.length === 10 ? `${value}T00:00:00` : value)) : '—';
// Slovenian count with singular, dual, few (3-4) and many forms, e.g. plural(3, ['član', 'člana', 'člani', 'članov']).
export const plural = (n: number, [one, two, few, many]: [string, string, string, string]) => `${n} ${n % 100 === 1 ? one : n % 100 === 2 ? two : n % 100 === 3 || n % 100 === 4 ? few : many}`;
// Case- and diacritic-insensitive text for client-side filtering.
export const fold = (value: string) => value.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
