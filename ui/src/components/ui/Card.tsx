import React, { HTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/utils'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  header?: ReactNode
  footer?: ReactNode
  hover?: boolean
  asChild?: boolean
}

export function Card({ className, header, footer, hover, children, asChild, ...props }: CardProps) {
  const cardClassName = cn(
    'rounded-lg border border-[#334155] bg-[#1e293b] shadow-md',
    hover && 'transition-all duration-200 hover:shadow-lg hover:-translate-y-1 hover:scale-[1.02]',
    className
  )

  const cardContent = (
    <>
      {header && (
        <div className="px-6 py-4 border-b border-[#334155]">{header}</div>
      )}
      <div className={cn('px-6 py-4', !header && !footer && 'px-6 py-4')}>{children}</div>
      {footer && (
        <div className="px-6 py-4 border-t border-[#334155]">{footer}</div>
      )}
    </>
  )

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as React.ReactElement, {
      className: cn(cardClassName, (children as React.ReactElement).props.className),
      ...props,
      children: cardContent,
    })
  }

  return (
    <div className={cardClassName} {...props}>
      {cardContent}
    </div>
  )
}

// Card sub-components for shadcn/ui compatibility
export function CardHeader({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('flex flex-col space-y-1.5 px-6 py-4', className)} {...props}>
      {children}
    </div>
  )
}

export function CardTitle({ className, children, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={cn('text-lg font-semibold leading-none tracking-tight text-white', className)} {...props}>
      {children}
    </h3>
  )
}

export function CardDescription({ className, children, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn('text-sm text-gray-400', className)} {...props}>
      {children}
    </p>
  )
}

export function CardContent({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('px-6 py-4', className)} {...props}>
      {children}
    </div>
  )
}
