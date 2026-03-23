import { FILE_ICONS } from '@/lib/constants';

interface FileIconProps {
  filename: string;
  className?: string;
}

export function FileIcon({ filename, className }: FileIconProps) {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const icon = FILE_ICONS[ext] || FILE_ICONS.default;
  return <span className={className}>{icon}</span>;
}
