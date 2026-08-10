import { LogOut } from 'lucide-react'
import { Button, Modal } from '@/components/ui'

interface LogoutConfirmationModalProps {
  open: boolean
  onClose: () => void
  onConfirm: () => void
}

export function LogoutConfirmationModal({ open, onClose, onConfirm }: LogoutConfirmationModalProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Log out"
      className="max-w-[420px] w-[calc(100%-32px)] sm:w-full"
      footer={
        <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose} className="w-full sm:w-auto">
            Cancel
          </Button>
          <Button
            type="button"
            variant="danger"
            onClick={onConfirm}
            className="w-full sm:w-auto gap-2"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </div>
      }
    >
      <div className="flex flex-col items-center text-center sm:items-start sm:text-left gap-4">
        <div className="h-12 w-12 rounded-xl bg-red-50 text-danger flex items-center justify-center shrink-0">
          <LogOut className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-text">Log out of InfluenceOS?</h3>
          <p className="mt-1.5 text-sm text-text-secondary leading-relaxed">
            Are you sure you want to log out of your account?
          </p>
          <p className="mt-1 text-xs text-text-secondary">
            You&apos;ll need to sign in again to access your workspace.
          </p>
        </div>
      </div>
    </Modal>
  )
}
