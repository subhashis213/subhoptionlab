/**
 * Bottom sheet modal — mobile-first overlay that slides up from the bottom.
 * Used for forms like "Add Leg", "Set SL", chip operations, etc.
 */
import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'

export default function BottomSheet({ isOpen, onClose, title, children }) {
  const sheetRef = useRef(null)

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="bottom-sheet-overlay" onClick={onClose}>
      <div
        className="bottom-sheet"
        ref={sheetRef}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bottom-sheet-header">
          <div className="bottom-sheet-handle" />
          <div className="bottom-sheet-title-row">
            <h3>{title}</h3>
            <button className="bottom-sheet-close" onClick={onClose}>
              <X size={20} />
            </button>
          </div>
        </div>
        <div className="bottom-sheet-content">
          {children}
        </div>
      </div>
    </div>
  )
}
