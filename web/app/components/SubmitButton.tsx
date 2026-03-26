'use client'

import React, { useState, useEffect } from 'react'
import * as ReactDOM from 'react-dom'

interface SubmitButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode
  loadingText?: string
}

// Safely access useFormStatus since Netlify SSR might trip up on direct exports 
// depending on the exact React 18 resolution.
const useFormStatusSafely = typeof (ReactDOM as any).useFormStatus === 'function' 
  ? (ReactDOM as any).useFormStatus 
  : typeof (ReactDOM as any).experimental_useFormStatus === 'function'
  ? (ReactDOM as any).experimental_useFormStatus
  : () => ({ pending: false });

export function SubmitButton({ children, loadingText = 'Loading...', className, onClick, ...props }: SubmitButtonProps) {
  const formStatus = useFormStatusSafely();
  const formPending = formStatus?.pending || false;
  
  // Fallback state if useFormStatus is unavailable
  const [internalPending, setInternalPending] = useState(false);

  // If the server action completes, internalPending should be reset. 
  // We can loosely detect this if the form action finishes but we are still here.
  useEffect(() => {
    if (internalPending) {
      const timeout = setTimeout(() => setInternalPending(false), 8000); // safety fallback
      return () => clearTimeout(timeout);
    }
  }, [internalPending]);

  const pending = formPending || internalPending;

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    // If not using formStatus natively, trigger internal fallback loader
    if (!formPending) {
      setInternalPending(true);
    }
    if (onClick) {
      onClick(e);
    }
  };

  return (
    <button
      type="submit"
      className={`${className || ''} ${pending ? 'opacity-75 cursor-not-allowed' : ''}`}
      disabled={pending || props.disabled}
      onClick={handleClick}
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
