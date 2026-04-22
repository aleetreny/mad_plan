import { useState } from 'react';
import { ImageIcon } from 'lucide-react';
import { cn } from '../lib/cn';

interface MediaCoverProps {
  src?: string | null;
  alt: string;
  className?: string;
  priority?: boolean;
  fallbackLabel?: string;
}

export function MediaCover({ src, alt, className, priority = false, fallbackLabel }: MediaCoverProps) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return (
      <div className={cn('flex h-full w-full items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.38),_transparent_55%),linear-gradient(135deg,var(--card),rgba(0,0,0,0.08))] text-muted-foreground', className)}>
        <div className="flex flex-col items-center gap-2 px-4 text-center">
          <ImageIcon className="h-8 w-8" />
          {fallbackLabel ? <span className="text-xs font-medium">{fallbackLabel}</span> : null}
        </div>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      loading={priority ? 'eager' : 'lazy'}
      fetchPriority={priority ? 'high' : 'auto'}
      onError={() => setFailed(true)}
    />
  );
}

