'use client'

import { useFormStatus } from 'react-dom'
import React from 'react'

interface SubmitButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode
  loadingText?: string
}

export function SubmitButton({ children, loadingText = 'Loading...', className, ...props }: SubmitButtonProps) {
  const { pending } = useFormStatus()

  return (
    <button
      type="submit"
      className={`${className} ${pending ? 'opacity-75 cursor-not-allowed' : ''}`}
      disabled={pending || props.disabled}
      {...props}
    >
      {pending ? (
        <>
          <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
          {loadingText}
        </>
      ) : (
        children
      )}
    </button>
  )
}
