import React, { HTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

interface AvatarProps extends HTMLAttributes<HTMLDivElement> {
  className?: string
}

export function Avatar({ className, children, ...props }: AvatarProps) {
  return (
    <div
      className={cn('relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full', className)}
      {...props}
    >
      {children}
    </div>
  )
}

interface AvatarFallbackProps extends HTMLAttributes<HTMLDivElement> {
  className?: string
}

export function AvatarFallback({ className, children, ...props }: AvatarFallbackProps) {
  return (
    <div
      className={cn(
        'flex h-full w-full items-center justify-center rounded-full bg-gray-800 text-gray-200',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

