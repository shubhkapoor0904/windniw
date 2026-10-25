type Props = {
  start: string
  end: string
  cutoff: string
  onStart: (value: string) => void
  onEnd: (value: string) => void
  onCutoff: (value: string) => void
  singleDate?: boolean
}

export default function Controls({
  start,
  end,
  cutoff,
  onStart,
  onEnd,
  onCutoff,
  singleDate = false,
}: Props) {
  return (
    <div className="controls-bar">
      <label className="control-group">
        <span className="control-label">{singleDate ? 'Delivery day' : 'From'}</span>
        <input
          className="control-input"
          type="date"
          min="2026-01-01"
          max="2026-01-31"
          value={start}
          onChange={(event) => onStart(event.target.value)}
        />
      </label>
      {!singleDate && (
        <label className="control-group">
          <span className="control-label">To</span>
          <input
            className="control-input"
            type="date"
            min="2026-01-01"
            max="2026-01-31"
            value={end}
            onChange={(event) => onEnd(event.target.value)}
          />
        </label>
      )}
      <label className="control-group">
        <span className="control-label">Decision cutoff · D-1 London time</span>
        <input
          className="control-input"
          type="time"
          value={cutoff}
          onChange={(event) => onCutoff(event.target.value)}
        />
      </label>
    </div>
  )
}
