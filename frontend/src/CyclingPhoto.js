import React, { useEffect, useState } from 'react'

// The homepage hero's rotating photo set. All from Unsplash (free for
// commercial use, no attribution required).
export const HERO_PHOTOS = [
  'https://images.unsplash.com/photo-1573496527892-904f897eb744?fm=jpg&q=80&w=900&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1581065178047-8ee15951ede6?fm=jpg&q=80&w=900&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1611432579402-7037e3e2c1e4?fm=jpg&q=80&w=900&auto=format&fit=crop',
]

// A separate set for the login/register branding panel — shot on a
// plain white studio backdrop rather than a real office background, so
// the circular fade mask (.auth-branding-photo) blends into the page's
// own light background almost seamlessly instead of fading out a busy
// scene. True background removal (isolating just the person from an
// arbitrary backdrop) isn't something this environment has a tool for;
// starting from an already-plain backdrop is the practical equivalent.
export const AUTH_PHOTOS = [
  'https://images.unsplash.com/photo-1610659523060-816c02b94529?fm=jpg&q=80&w=900&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1590086782792-42dd2350140d?fm=jpg&q=80&w=900&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1623366302587-b38b1ddaefd9?fm=jpg&q=80&w=900&auto=format&fit=crop',
]

// Cross-fades between a fixed set of images on an interval — every
// image is always mounted (just at opacity 0), so there's never a
// blank/broken frame while a new one loads. Sizing/shape (aspect-ratio,
// border-radius, filter, box-shadow, ...) is applied via `className` to
// this component's own wrapper div, not to the <img> tags — the same
// classNames that used to style a single <img> directly (e.g.
// .warm-hero-photo) work unchanged here.
export default function CyclingPhoto({ images, intervalMs = 8000, className, alt }) {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (images.length <= 1) return undefined
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % images.length)
    }, intervalMs)
    return () => clearInterval(id)
  }, [images, intervalMs])

  return (
    <div className={`cycling-photo${className ? ` ${className}` : ''}`}>
      {images.map((src, i) => (
        <img
          key={src}
          src={src}
          alt={i === index ? alt : ''}
          aria-hidden={i === index ? undefined : true}
          className={`cycling-photo-img${i === index ? ' cycling-photo-active' : ''}`}
        />
      ))}
    </div>
  )
}
