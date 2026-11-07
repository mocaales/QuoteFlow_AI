// The forms take percentages, the API takes fractions.
export const fraction = (value: FormDataEntryValue | string | null) => String(Number((Number(value || 0) / 100).toFixed(6)));
export const percentValue = (value: string) => String(Number((Number(value) * 100).toFixed(4)));
