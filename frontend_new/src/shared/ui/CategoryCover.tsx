import { useEffect, useRef, useState } from 'react';
import { categoryMeta } from '../../domain/madplan/constants';
import { cn } from '../lib/cn';

interface CategoryCoverProps {
  src?: string | null;
  alt: string;
  category?: string | null;
  /** Seed (event id) so each cover gets a stable, slightly different look. */
  seed?: string;
  className?: string;
  priority?: boolean;
  /** Icon size in px for the fallback cover. */
  iconSize?: number;
  showLabel?: boolean;
}

/** How long a remote image may stay pending before we swap in the cover. */
const IMAGE_LOAD_TIMEOUT_MS = 8000;

function hashSeed(seed: string): number {
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) | 0;
  }
  return Math.abs(hash);
}

export function GeneratedCover({
  category,
  seed = '',
  className,
  iconSize = 44,
  showLabel = false,
}: Pick<CategoryCoverProps, 'category' | 'seed' | 'className' | 'iconSize' | 'showLabel'>) {
  const meta = categoryMeta(category);
  const Icon = meta.icon;
  const hash = hashSeed(seed || category || 'madplan');
  const angle = 115 + (hash % 90); // 115°-205°: always downward, never harsh
  const patternShift = hash % 24;

  return (
    <div
      aria-hidden="true"
      className={cn('relative flex h-full w-full items-center justify-center overflow-hidden', className)}
      style={{ background: `linear-gradient(${angle}deg, ${meta.from}, ${meta.to})` }}
    >
      {/* Subtle texture so covers do not read as flat blocks. */}
      <div
        className="absolute inset-0 opacity-[0.14]"
        style={{
          backgroundImage: 'radial-gradient(rgba(255,255,255,0.9) 1px, transparent 1.4px)',
          backgroundSize: '22px 22px',
          backgroundPosition: `${patternShift}px ${patternShift / 2}px`,
        }}
      />
      <div
        className="absolute -right-8 -top-10 h-44 w-44 rounded-full opacity-[0.16]"
        style={{ background: 'radial-gradient(circle, rgba(255,255,255,0.95), transparent 70%)' }}
      />
      <div className="relative flex flex-col items-center gap-2 text-white/92">
        <Icon strokeWidth={1.5} style={{ width: iconSize, height: iconSize }} />
        {showLabel ? (
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-white/85">{meta.short}</span>
        ) : null}
      </div>
    </div>
  );
}

export function CategoryCover({
  src,
  alt,
  category,
  seed,
  className,
  priority = false,
  iconSize,
  showLabel,
}: CategoryCoverProps) {
  // Tracking the failed URL (instead of a boolean) makes the flag reset
  // automatically when `src` changes, without extra state writes in effects.
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const failed = failedSrc !== null && failedSrc === src;

  useEffect(() => {
    if (!src) return;
    const node = imgRef.current;
    if (!node) return;

    // Lazy images outside the viewport never load until scrolled into view,
    // so the stall timer must only start once the image is actually visible.
    let timer: number | undefined;
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      timer = window.setTimeout(() => {
        const current = imgRef.current;
        if (current && !current.complete) setFailedSrc(src);
      }, IMAGE_LOAD_TIMEOUT_MS);
    });
    observer.observe(node);

    return () => {
      observer.disconnect();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [src]);

  if (!src || failed) {
    return (
      <GeneratedCover
        category={category}
        seed={seed || alt}
        className={className}
        iconSize={iconSize}
        showLabel={showLabel}
      />
    );
  }

  return (
    <img
      ref={imgRef}
      src={src}
      alt={alt}
      className={cn('h-full w-full object-cover', className)}
      loading={priority ? 'eager' : 'lazy'}
      fetchPriority={priority ? 'high' : 'auto'}
      referrerPolicy="no-referrer"
      onError={() => setFailedSrc(src)}
    />
  );
}
