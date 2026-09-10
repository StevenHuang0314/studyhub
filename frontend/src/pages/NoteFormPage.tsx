import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

/** Backs both /notes/new and /notes/:id/edit. */
export default function NoteFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { user } = useAuth()

  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [courseCode, setCourseCode] = useState('')
  const [tags, setTags] = useState('')
  const [resourceUrl, setResourceUrl] = useState('')

  const [loading, setLoading] = useState(isEdit)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isEdit) return
    let cancelled = false
    api
      .getNote(Number(id))
      .then((note) => {
        if (cancelled) return
        if (user && note.author.id !== user.id) {
          setError('You can only edit your own notes.')
          return
        }
        setTitle(note.title)
        setContent(note.content)
        setCourseCode(note.course_code)
        setTags(note.tags.join(', '))
        setResourceUrl(note.resource_url)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load this note')
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
      title,
      content,
      course_code: courseCode,
      tags: tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
      resource_url: resourceUrl,
    }
    try {
      const note = isEdit
        ? await api.updateNote(Number(id), payload)
        : await api.createNote(payload)
      navigate(`/notes/${note.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save this note')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <p className="muted center">Loading…</p>

  return (
    <div className="narrow">
      <h1>{isEdit ? 'Edit note' : 'Post a note'}</h1>

      <form className="panel" onSubmit={handleSubmit}>
        {error && <p className="error">{error}</p>}

        <label>
          Title
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="CS 400 — Red-black tree rotations, worked through"
            minLength={3}
            maxLength={160}
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
          Notes
          <textarea
            rows={12}
            value={content}
            onChange={(event) => setContent(event.target.value)}
            placeholder="Paste your notes, summary or walkthrough here…"
            required
          />
        </label>

        <label>
          Tags
          <input
            value={tags}
            onChange={(event) => setTags(event.target.value)}
            placeholder="exam-prep, trees, recursion"
          />
          <small className="muted">Comma separated, up to 8.</small>
        </label>

        <label>
          Link to a file or slides (optional)
          <input
            type="url"
            value={resourceUrl}
            onChange={(event) => setResourceUrl(event.target.value)}
            placeholder="https://drive.google.com/…"
          />
        </label>

        <div className="row">
          <button className="button" type="submit" disabled={submitting}>
            {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Post note'}
          </button>
          <button type="button" className="button ghost" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
