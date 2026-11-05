import { useId, type ReactNode } from 'react'
import Modal from './Modal'

/** "Are you sure?" for admin actions that change what pupils get (English, like the admin pages). */
export default function ConfirmDialog({
  open,
  title,
  children,
  confirm,
  danger = false,
  busy = false,
  onConfirm,
  onClose,
}: {
  open: boolean
  title: string
  children: ReactNode
  confirm: string
  danger?: boolean
  busy?: boolean
  onConfirm: () => void
  onClose: () => void
}) {
  const id = useId()
  return (
    <Modal open={open} onClose={onClose} labelledBy={id}>
      <div className="flex flex-col gap-4 text-start" dir="ltr" lang="en">
        <h2 id={id} className="text-xl font-black text-ink">
          {title}
        </h2>
        <div className="flex flex-col gap-2 font-bold text-ink-2">{children}</div>
        <div className="flex flex-wrap justify-end gap-2">
          <button type="button" onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className={danger ? 'btn-primary bg-danger hover:bg-danger' : 'btn-primary'}
          >
            {busy ? '⏳ Working…' : confirm}
          </button>
        </div>
      </div>
    </Modal>
  )
}
