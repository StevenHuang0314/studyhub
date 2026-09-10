import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import NoteCard from '../components/NoteCard'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { Note, NoteSort } from '../types'

const PAGE_SIZE = 9

export default function NotesPage() {
  const { user } = useAuth()

  const [notes, setNotes] = useState<Note[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [courses, setCourses] = useState<string[]>([])

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [course, setCourse] = useState('')
  const [sort, setSort] = useState<NoteSort>('newest')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Debounce the search box so typing doesn't fire a request per keystroke.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput)
      setPage(0)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const loadNotes = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.listNotes({
        search: search || undefined,
        course_code: course || undefined,
        sort,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      })
      setNotes(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load notes')
    } finally {
      setLoading(false)
    }
  }, [search, course, sort, page])

  useEffect(() => {
    void loadNotes()
  }, [loadNotes])

  useEffect(() => {
    api.listCourses().then(setCourses).catch(() => setCourses([]))
  }, [])

  const lastPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1)

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Shared notes</h1>
          <p className="muted">
            {total} resource{total === 1 ? '' : 's'} posted by students.
          </p>
        </div>
        {user && (
          <Link className="button" to="/notes/new">
            Post a note
          </Link>
        )}
      </div>

      <div className="filters">
        <input
          className="grow"
          placeholder="Search titles and content…"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
        />
        <select
          value={course}
          onChange={(event) => {
            setCourse(event.target.value)
            setPage(0)
          }}
        >
          <option value="">All courses</option>
          {courses.map((code) => (
            <option key={code} value={code}>
              {code}
            </option>
          ))}
        </select>
        <select
          value={sort}
          onChange={(event) => {
            setSort(event.target.value as NoteSort)
            setPage(0)
          }}
        >
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
          <option value="top_rated">Highest rated</option>
          <option value="most_rated">Most reviewed</option>
        </select>
      </div>

      {error && <p className="error">{error}</p>}
      {loading ? (
        <p className="muted center">Loading notes…</p>
      ) : notes.length === 0 ? (
        <p className="muted center">
          Nothing here yet. {user ? <Link to="/notes/new">Post the first note</Link> : 'Sign in to post one.'}
        </p>
      ) : (
        <div className="grid">
          {notes.map((note) => (
            <NoteCard key={note.id} note={note} />
          ))}
        </div>
      )}

      {lastPage > 0 && (
        <div className="pager">
          <button
            type="button"
            className="button ghost"
            disabled={page === 0}
            onClick={() => setPage((current) => current - 1)}
          >
            Previous
          </button>
          <span className="muted">
            Page {page + 1} of {lastPage + 1}
          </span>
          <button
            type="button"
            className="button ghost"
            disabled={page >= lastPage}
            onClick={() => setPage((current) => current + 1)}
          >
            Next
          </button>
        </div>
      )}
    </>
  )
}
