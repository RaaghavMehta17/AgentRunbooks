import { HTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circular' | 'rectangular'
  lines?: number
}

export function Skeleton({ className, variant = 'rectangular', lines = 1, ...props }: SkeletonProps) {
  if (variant === 'text' && lines > 1) {
    return (
      <div className={cn('space-y-2', className)} {...props}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={cn(
              'h-4 bg-gray-700 rounded animate-shimmer',
              i === lines - 1 && 'w-3/4'
            )}
            style={{
              background: 'linear-gradient(90deg, #334155 25%, #475569 50%, #334155 75%)',
              backgroundSize: '200% 100%',
              animation: 'shimmer 2s linear infinite',
            }}
          />
        ))}
      </div>
    )
  }

  const baseStyles = 'bg-gray-700 rounded animate-shimmer'
  const variantStyles = {
    text: 'h-4',
    circular: 'rounded-full aspect-square',
    rectangular: 'h-20',
  }

  return (
    <div
      className={cn(baseStyles, variantStyles[variant], className)}
      style={{
        background: 'linear-gradient(90deg, #334155 25%, #475569 50%, #334155 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 2s linear infinite',
      }}
      {...props}
    />
  )
}

