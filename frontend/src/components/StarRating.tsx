interface StarRatingProps {
  value: number | null
  count?: number
  /** When provided the stars become buttons and the widget is interactive. */
  onChange?: (score: number) => void
  size?: 'sm' | 'lg'
}

export default function StarRating({ value, count, onChange, size = 'sm' }: StarRatingProps) {
  const rounded = Math.round(value ?? 0)
  const stars = [1, 2, 3, 4, 5]

  if (!onChange) {
    return (
      <span className={`stars ${size}`} title={value ? `${value} out of 5` : 'Not rated yet'}>
        {stars.map((star) => (
          <span key={star} className={star <= rounded ? 'star on' : 'star'}>
            ★
          </span>
        ))}
        <span className="stars-meta">
          {value === null ? 'no ratings yet' : `${value.toFixed(1)}${count ? ` (${count})` : ''}`}
        </span>
      </span>
    )
  }

  return (
    <span className={`stars ${size} interactive`}>
      {stars.map((star) => (
        <button
          key={star}
          type="button"
          className={star <= rounded ? 'star on' : 'star'}
          aria-label={`Rate ${star} out of 5`}
          onClick={() => onChange(star)}
        >
          ★
        </button>
      ))}
    </span>
  )
}
