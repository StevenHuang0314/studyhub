import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import StarRating from '../components/StarRating'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { Note, Rating } from '../types'

export default function NoteDetailPage() {
  const { id } = useParams()
  const noteId = Number(id)
  const navigate = useNavigate()
  const { user } = useAuth()

  const [note, setNote] = useState<Note | null>(null)
  const [ratings, setRatings] = useState<Rating[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [score, setScore] = useState(0)
  const [comment, setComment] = useState('')
  const [ratingError, setRatingError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [fetchedNote, fetchedRatings] = await Promise.all([
        api.getNote(noteId),
        api.listRatings(noteId),
      ])
      setNote(fetchedNote)
      setRatings(fetchedRatings)

      const mine = user ? fetchedRatings.find((rating) => rating.user.id === user.id) : undefined
      setScore(mine?.score ?? 0)
      setComment(mine?.comment ?? '')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load this note')
    } finally {
      setLoading(false)
    }
  }, [noteId, user])

  useEffect(() => {
    void load()
  }, [load])

  async function submitRating(event: FormEvent) {
    event.preventDefault()
    setRatingError('')
    if (score < 1) {
      setRatingError('Pick a star rating first')
      return
    }
    try {
      await api.rateNote(noteId, score, comment)
      await load()
    } catch (err) {
      setRatingError(err instanceof Error ? err.message : 'Could not save your rating')
    }
  }

  async function removeRating() {
    try {
      await api.deleteMyRating(noteId)
      setScore(0)
      setComment('')
      await load()
    } catch (err) {
      setRatingError(err instanceof Error ? err.message : 'Could not remove your rating')
    }
  }

  async function deleteNote() {
    if (!window.confirm('Delete this note? This cannot be undone.')) return
    try {
      await api.deleteNote(noteId)
      navigate('/notes')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete this note')
    }
  }

  if (loading) return <p className="muted center">Loading…</p>
  if (error) return <p className="error">{error}</p>
  if (!note) return null

  const isAuthor = user?.id === note.author.id
  const myRating = user ? ratings.find((rating) => rating.user.id === user.id) : undefined

  return (
    <article className="detail">
      <Link className="back" to="/notes">
        ← All notes
      </Link>

      <div className="page-head">
        <div>
          <span className="pill">{note.course_code}</span>
          <h1>{note.title}</h1>
          <p className="muted">
            by @{note.author.username} · updated {new Date(note.updated_at).toLocaleDateString()}
          </p>
          <StarRating value={note.average_rating} count={note.rating_count} size="lg" />
        </div>

        {isAuthor && (
          <div className="row">
            <Link className="button ghost" to={`/notes/${note.id}/edit`}>
              Edit
            </Link>
            <button type="button" className="button danger" onClick={deleteNote}>
              Delete
            </button>
          </div>
        )}
      </div>

      <div className="panel prose">{note.content}</div>

      {note.resource_url && (
        <p>
          <a href={note.resource_url} target="_blank" rel="noreferrer">
            Attached resource ↗
          </a>
        </p>
      )}

      {note.tags.length > 0 && (
        <p className="tags">
          {note.tags.map((tag) => (
            <span key={tag} className="tag">
              #{tag}
            </span>
          ))}
        </p>
      )}

      <section>
        <h2>Reviews ({ratings.length})</h2>

        {!user && (
          <p className="muted">
            <Link to="/login">Sign in</Link> to rate this note.
          </p>
        )}

        {user && isAuthor && <p className="muted">You can't rate your own note.</p>}

        {user && !isAuthor && (
          <form className="panel" onSubmit={submitRating}>
            {ratingError && <p className="error">{ratingError}</p>}
            <div className="row space-between">
              <StarRating value={score} onChange={setScore} size="lg" />
              {myRating && (
                <button type="button" className="button ghost" onClick={removeRating}>
                  Remove my rating
                </button>
              )}
            </div>
            <label>
              Comment (optional)
              <textarea
                rows={3}
                maxLength={500}
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                placeholder="What made these notes useful?"
              />
            </label>
            <button className="button" type="submit">
              {myRating ? 'Update review' : 'Post review'}
            </button>
          </form>
        )}

        {ratings.length === 0 ? (
          <p className="muted">No reviews yet.</p>
        ) : (
          <ul className="reviews">
            {ratings.map((rating) => (
              <li key={rating.id}>
                <div className="row space-between">
                  <strong>@{rating.user.username}</strong>
                  <StarRating value={rating.score} />
                </div>
                {rating.comment && <p>{rating.comment}</p>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </article>
  )
}
