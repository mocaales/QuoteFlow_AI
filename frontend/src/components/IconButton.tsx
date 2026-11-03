import type { ButtonHTMLAttributes } from 'react';
import Icon, { type IconName } from './Icon';
// Icon-only action: `label` is the accessible name (may name the object), `tip` the short visible tooltip.
export default function IconButton({ icon, label, tip, className = '', ...rest }: { icon: IconName; label: string; tip?: string } & ButtonHTMLAttributes<HTMLButtonElement>) {
 return <button type="button" {...rest} className={`icon-action ${className}`} aria-label={label} data-tip={tip ?? label}><Icon name={icon}/></button>;
}
