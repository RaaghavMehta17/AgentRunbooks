import React, { createContext, useContext, useState, HTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/utils'

interface CollapsibleContextValue {
  open: boolean
  setOpen: (open: boolean) => void
}

const CollapsibleContext = createContext<CollapsibleContextValue | undefined>(undefined)

function useCollapsible() {
  const context = useContext(CollapsibleContext)
  if (!context) throw new Error('Collapsible components must be used within Collapsible')
  return context
}

interface CollapsibleProps {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  children: ReactNode
}

export function Collapsible({ open: controlledOpen, onOpenChange, children }: CollapsibleProps) {
  const [internalOpen, setInternalOpen] = useState(false)
  const isControlled = controlledOpen !== undefined
  const open = isControlled ? controlledOpen : internalOpen

  const setOpen = (newOpen: boolean) => {
    if (!isControlled) {
      setInternalOpen(newOpen)
    }
    onOpenChange?.(newOpen)
  }

  return (
    <CollapsibleContext.Provider value={{ open, setOpen }}>
      {children}
    </CollapsibleContext.Provider>
  )
}

interface CollapsibleTriggerProps extends HTMLAttributes<HTMLElement> {
  asChild?: boolean
}

export function CollapsibleTrigger({ asChild, children, ...props }: CollapsibleTriggerProps) {
  const { open, setOpen } = useCollapsible()

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as React.ReactElement, {
      onClick: (e: React.MouseEvent) => {
        setOpen(!open)
        if ((children as React.ReactElement).props.onClick) {
          ;(children as React.ReactElement).props.onClick(e)
        }
      },
    })
  }

  return (
    <button onClick={() => setOpen(!open)} {...props}>
      {children}
    </button>
  )
}

interface CollapsibleContentProps extends HTMLAttributes<HTMLDivElement> {}

export function CollapsibleContent({ className, children, ...props }: CollapsibleContentProps) {
  const { open } = useCollapsible()

  if (!open) return null

  return (
    <div className={cn('overflow-hidden', className)} {...props}>
      {children}
    </div>
  )
}

