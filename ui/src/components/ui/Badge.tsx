import { HTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'secondary'
  size?: 'sm' | 'md' | 'lg'
  pulse?: boolean
  icon?: React.ReactNode
}

export function Badge({ className, variant = 'neutral', size = 'md', pulse, icon, children, ...props }: BadgeProps) {
  const variants = {
    success: 'bg-[#10b981]/20 text-[#10b981] border-[#10b981]/30',
    warning: 'bg-[#f59e0b]/20 text-[#f59e0b] border-[#f59e0b]/30',
    error: 'bg-[#ef4444]/20 text-[#ef4444] border-[#ef4444]/30',
    info: 'bg-[#3b82f6]/20 text-[#3b82f6] border-[#3b82f6]/30',
    neutral: 'bg-[#334155] text-gray-300 border-[#475569]',
    secondary: 'bg-[#334155] text-gray-300 border-[#475569]',
  }

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        variants[variant],
        sizes[size],
        pulse && 'animate-pulse-slow',
        className
      )}
      {...props}
    >
      {icon && <span className="w-3 h-3">{icon}</span>}
      {children}
    </span>
  )
}

