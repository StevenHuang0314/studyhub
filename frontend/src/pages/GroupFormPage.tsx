import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

/** Backs both /groups/new and /groups/:id/edit. */
export default function GroupFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { user } = useAuth()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [courseCode, setCourseCode] = useState('')
  const [meetingTime, setMeetingTime] = useState('')
  const [location, setLocation] = useState('')
  const [capacity, setCapacity] = useState(6)

  const [loading, setLoading] = useState(isEdit)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isEdit) return
    let cancelled = false
    api
      .getGroup(Number(id))
      .then((group) => {
        if (cancelled) return
        if (user && group.owner.id !== user.id) {
          setError('Only the group owner can edit this group.')
          return
        }
        setName(group.name)
        setDescription(group.description)
        setCourseCode(group.course_code)
        setMeetingTime(group.meeting_time)
        setLocation(group.location)
        setCapacity(group.capacity)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load this group')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, isEdit, user])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    const payload = {
      name,
      description,
      course_code: courseCode,
      meeting_time: meetingTime,
      location,
      capacity,
    }
    try {
      const group = isEdit
        ? await api.updateGroup(Number(id), payload)
        : await api.createGroup(payload)
      navigate(`/groups/${group.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save this group')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <p className="muted center">Loading…</p>

  return (
    <div className="narrow">
      <h1>{isEdit ? 'Edit study group' : 'Start a study group'}</h1>

      <form className="panel" onSubmit={handleSubmit}>
        {error && <p className="error">{error}</p>}

        <label>
          Group name
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="CS 400 Sunday problem sets"
            minLength={3}
            maxLength={120}
            required
          />
        </label>

        <label>
          Course code
          <input
            value={courseCode}
            onChange={(event) => setCourseCode(event.target.value)}
            placeholder="CS400"
            required
          />
        </label>

        <label>
          Description
          <textarea
            rows={5}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="How the group works, what to bring, who it's for…"
          />
        </label>

        <div className="row">
          <label className="grow">
            When
            <input
              value={meetingTime}
              onChange={(event) => setMeetingTime(event.target.value)}
              placeholder="Sundays 2-4pm"
            />
          </label>
          <label className="grow">
            Where
            <input
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              placeholder="College Library, 3rd floor"
            />
          </label>
        </div>

        <label>
          Capacity
          <input
            type="number"
            min={2}
            max={100}
            value={capacity}
            onChange={(event) => setCapacity(Number(event.target.value))}
            required
          />
        </label>

        <div className="row">
          <button className="button" type="submit" disabled={submitting}>
            {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Create group'}
          </button>
          <button type="button" className="button ghost" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
