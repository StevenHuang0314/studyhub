import { Link } from 'react-router-dom'
import type { Group } from '../types'

export default function GroupCard({ group }: { group: Group }) {
  return (
    <article className="card">
      <div className="card-head">
        <span className="pill">{group.course_code}</span>
        <span className={group.is_full ? 'badge full' : 'badge'}>
          {group.member_count}/{group.capacity} members
        </span>
      </div>

      <h3>
        <Link to={`/groups/${group.id}`}>{group.name}</Link>
      </h3>

      <p className="excerpt">{group.description || 'No description yet.'}</p>

      <div className="card-foot">
        <span className="muted">{group.meeting_time || 'Time TBD'}</span>
        <span className="muted">{group.location || 'Location TBD'}</span>
      </div>
    </article>
  )
}
