import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import GroupCard from '../components/GroupCard'
import NoteCard from '../components/NoteCard'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { Group, Note } from '../types'

export default function DashboardPage() {
  const { user } = useAuth()
  const [notes, setNotes] = useState<Note[]>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    Promise.all([api.myNotes(), api.myGroups()])
      .then(([myNotes, myGroups]) => {
        if (cancelled) return
        setNotes(myNotes)
        setGroups(myGroups)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load your data')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) return <p className="muted center">Loading…</p>

  const reviewsReceived = notes.reduce((sum, note) => sum + note.rating_count, 0)
  const rated = notes.filter((note) => note.average_rating !== null)
  const averageScore =
    rated.length > 0
      ? rated.reduce((sum, note) => sum + (note.average_rating ?? 0), 0) / rated.length
      : null

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Hey @{user?.username}</h1>
          <p className="muted">Everything you've posted and joined.</p>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="stats">
        <div className="stat">
          <span className="stat-value">{notes.length}</span>
          <span className="stat-label">notes posted</span>
        </div>
        <div className="stat">
          <span className="stat-value">{reviewsReceived}</span>
          <span className="stat-label">reviews received</span>
        </div>
        <div className="stat">
          <span className="stat-value">{averageScore ? averageScore.toFixed(1) : '—'}</span>
          <span className="stat-label">average rating</span>
        </div>
        <div className="stat">
          <span className="stat-value">{groups.length}</span>
          <span className="stat-label">study groups</span>
        </div>
      </div>

      <section>
        <div className="page-head">
          <h2>My notes</h2>
          <Link className="button ghost" to="/notes/new">
            Post a note
          </Link>
        </div>
        {notes.length === 0 ? (
          <p className="muted">You haven't posted any notes yet.</p>
        ) : (
          <div className="grid">
            {notes.map((note) => (
              <NoteCard key={note.id} note={note} />
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="page-head">
          <h2>My study groups</h2>
          <Link className="button ghost" to="/groups/new">
            Start a group
          </Link>
        </div>
        {groups.length === 0 ? (
          <p className="muted">
            You haven't joined a group yet. <Link to="/groups">Browse groups</Link>.
          </p>
        ) : (
          <div className="grid">
            {groups.map((group) => (
              <GroupCard key={group.id} group={group} />
            ))}
          </div>
        )}
      </section>
    </>
  )
}
