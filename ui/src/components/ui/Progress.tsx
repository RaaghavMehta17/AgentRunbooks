import { HTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  value: number
  max?: number
  className?: string
}

export function Progress({ value, max = 100, className, ...props }: ProgressProps) {
  // Calculate percentage - value should be between 0 and max
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

  // Extract height class if present, default to h-2
  const heightMatch = className?.match(/h-(\d+|\[.*?\])/)
  const heightClass = heightMatch ? heightMatch[0] : 'h-2'
  
  // Determine color based on percentage or className
  let backgroundColor = '#3b82f6' // default primary-light blue
  if (className?.includes('[&>div]:bg-')) {
    if (className.includes('[&>div]:bg-success')) {
      backgroundColor = '#10b981' // success green
    } else if (className.includes('[&>div]:bg-warning')) {
      backgroundColor = '#f59e0b' // warning orange
    } else if (className.includes('[&>div]:bg-error') || className.includes('[&>div]:bg-destructive')) {
      backgroundColor = '#ef4444' // error red
    }
  } else if (percentage >= 90) {
    backgroundColor = '#10b981' // success green
  } else if (percentage >= 70) {
    backgroundColor = '#f59e0b' // warning orange
  } else {
    backgroundColor = '#ef4444' // error red
  }
  
  // Remove color and height classes from outer className
  const outerClassName = className
    ?.replace(/\[&>div\]:bg-\w+/g, '')
    .replace(/h-\d+|h-\[.*?\]/g, '')
    .trim() || ''

  return (
    <div
      className={cn('relative w-full overflow-hidden rounded-full bg-gray-700', heightClass, outerClassName)}
      style={{ minHeight: '8px' }}
      {...props}
    >
      <div
        className="h-full rounded-full transition-all duration-300 ease-in-out"
        style={{ 
          width: `${percentage}%`,
          backgroundColor: backgroundColor,
          minWidth: percentage > 0 ? '2px' : '0',
          height: '100%'
        }}
      />
    </div>
  )
}
