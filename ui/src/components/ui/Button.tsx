import React, { ButtonHTMLAttributes, forwardRef } from 'react'
import { cn } from '../../lib/utils'
import { Loader2 } from 'lucide-react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'ghost' | 'link' | 'outline' | 'default'
  size?: 'xs' | 'sm' | 'md' | 'lg'
  loading?: boolean
  icon?: React.ReactNode
  iconPosition?: 'left' | 'right'
  asChild?: boolean
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading, icon, iconPosition = 'left', children, disabled, asChild, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-light disabled:opacity-50 disabled:cursor-not-allowed'
    
    const variants = {
      primary: 'bg-[#3b82f6] text-white hover:bg-[#60a5fa] active:scale-95',
      default: 'bg-[#3b82f6] text-white hover:bg-[#60a5fa] active:scale-95',
      secondary: 'bg-[#334155] text-gray-200 hover:bg-[#475569] active:scale-95',
      outline: 'border border-[#334155] bg-transparent text-gray-200 hover:bg-[#1e293b] active:scale-95',
      danger: 'bg-[#ef4444] text-white hover:bg-[#f87171] active:scale-95',
      ghost: 'text-gray-300 hover:bg-[#1e293b] active:scale-95',
      link: 'text-[#3b82f6] hover:underline active:scale-95',
    }

    const sizes = {
      xs: 'px-2 py-1 text-xs rounded-md',
      sm: 'px-3 py-1.5 text-sm rounded-md',
      md: 'px-4 py-2 text-base rounded-lg',
      lg: 'px-6 py-3 text-lg rounded-lg',
    }

    const buttonContent = (
      <>
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin mr-2" />
        ) : icon && iconPosition === 'left' ? (
          <span className="mr-2">{icon}</span>
        ) : null}
        {children}
        {icon && iconPosition === 'right' && !loading ? (
          <span className="ml-2">{icon}</span>
        ) : null}
      </>
    )

    if (asChild && typeof children === 'object' && children !== null && 'type' in children) {
      // If asChild is true and children is a React element, clone it with our props
      return React.cloneElement(children as React.ReactElement, {
        className: cn(baseStyles, variants[variant], sizes[size], className),
        disabled: disabled || loading,
        ...props,
      })
    }

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        disabled={disabled || loading}
        {...props}
      >
        {buttonContent}
      </button>
    )
  }
)

Button.displayName = 'Button'

export default Button

