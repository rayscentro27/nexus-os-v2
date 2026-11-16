// Nova avatar media: NovaVid2 (muted, autoplay, loop) with a static portrait fallback.
// Honors prefers-reduced-motion and falls back to the portrait if the video cannot play.
import React, { forwardRef, useEffect, useState } from 'react';
import { ASSETS } from '../../data/assets';

export const usePrefersReducedMotion = () => {
  const query = '(prefers-reduced-motion: reduce)';
  const [reduced, setReduced] = useState(() => typeof window !== 'undefined' && !!window.matchMedia?.(query).matches);
  useEffect(() => {
    const mq = window.matchMedia?.(query);
    if (!mq) return;
    const on = () => setReduced(mq.matches);
    mq.addEventListener?.('change', on);
    return () => mq.removeEventListener?.('change', on);
  }, []);
  return reduced;
};

type Props = React.VideoHTMLAttributes<HTMLVideoElement> & { className?: string };

export const NovaVideo = forwardRef<HTMLVideoElement, Props>(({ className, muted = true, ...rest }, ref) => {
  const reduced = usePrefersReducedMotion();
  const [failed, setFailed] = useState(false);
  if (reduced || failed) {
    return <img src={ASSETS.novaAvatar} alt={String(rest['aria-label'] || 'Nova')} className={className} />;
  }
  return (
    <video
      ref={ref}
      src={ASSETS.novaVideoAvatar}
      poster={ASSETS.novaAvatar}
      autoPlay
      loop
      muted={muted}
      playsInline
      preload="metadata"
      onError={() => setFailed(true)}
      className={className}
      {...rest}
    />
  );
});
NovaVideo.displayName = 'NovaVideo';
