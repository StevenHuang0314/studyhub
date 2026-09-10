import { Link } from 'react-router-dom'
import StarRating from './StarRating'
import type { Note } from '../types'

export default function NoteCard({ note }: { note: Note }) {
  return (
    <article className="card">
      <div className="card-head">
        <span className="pill">{note.course_code}</span>
        <StarRating value={note.average_rating} count={note.rating_count} />
      </div>

      <h3>
        <Link to={`/notes/${note.id}`}>{note.title}</Link>
      </h3>

      <p className="excerpt">{note.content}</p>

      <div className="card-foot">
        <span className="muted">by @{note.author.username}</span>
        <span className="tags">
          {note.tags.map((tag) => (
            <span key={tag} className="tag">
              #{tag}
            </span>
          ))}
        </span>
      </div>
    </article>
  )
}
