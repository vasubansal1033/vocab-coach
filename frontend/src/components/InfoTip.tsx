import { useId } from 'react'

type Props = {
  label: string
  definition: string
}

/** Accessible hover/focus tip. No tooltip library: definitions are short and static. */
export default function InfoTip({ label, definition }: Props) {
  const tipId = useId()
  return (
    <span className="info-tip">
      <button type="button" className="info-tip-trigger" aria-describedby={tipId}>
        {label}
        <span className="info-tip-mark" aria-hidden="true">
          ?
        </span>
      </button>
      <span role="tooltip" id={tipId} className="info-tip-bubble">
        {definition}
      </span>
    </span>
  )
}
