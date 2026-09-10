import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { Group } from '../types'

export default function GroupDetailPage() {
  const { id } = useParams()
  const groupId = Number(id)
  const navigate = useNavigate()
  const { user } = useAuth()

  const [group, setGroup] = useState<Group | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [working, setWorking] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setGroup(await api.getGroup(groupId))
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load this group')
    } finally {
      setLoading(false)
    }
  }, [groupId])

  useEffect(() => {
    void load()
  }, [load])

  async function toggleMembership(join: boolean) {
    setActionError('')
    setWorking(true)
    try {
      if (join) await api.joinGroup(groupId)
      else await api.leaveGroup(groupId)
      await load()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'That did not work')
    } finally {
      setWorking(false)
    }
  }

  async function deleteGroup() {
    if (!window.confirm('Delete this group? Members will lose access.')) return
    try {
      await api.deleteGroup(groupId)
      navigate('/groups')
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not delete this group')
    }
  }

  if (loading) return <p className="muted center">Loading…</p>
  if (error) return <p className="error">{error}</p>
  if (!group) return null

  const isOwner = user?.id === group.owner.id
  const isMember = Boolean(user && group.members.some((member) => member.id === user.id))

  return (
    <article className="detail">
      <Link className="back" to="/groups">
        ← All study groups
      </Link>

      <div className="page-head">
        <div>
          <span className="pill">{group.course_code}</span>
          <h1>{group.name}</h1>
          <p className="muted">
            started by @{group.owner.username} · {group.member_count}/{group.capacity} members
          </p>
        </div>

        <div className="row">
          {isOwner ? (
            <>
              <Link className="button ghost" to={`/groups/${group.id}/edit`}>
                Edit
              </Link>
              <button type="button" className="button danger" onClick={deleteGroup}>
                Delete
              </button>
            </>
          ) : user ? (
            isMember ? (
              <button
                type="button"
                className="button ghost"
                disabled={working}
                onClick={() => toggleMembership(false)}
              >
                Leave group
              </button>
            ) : (
              <button
                type="button"
                className="button"
                disabled={working || group.is_full}
                onClick={() => toggleMembership(true)}
              >
                {group.is_full ? 'Group is full' : 'Join group'}
              </button>
            )
          ) : (
            <Link className="button" to="/login">
              Sign in to join
            </Link>
          )}
        </div>
      </div>

      {actionError && <p className="error">{actionError}</p>}

      <div className="panel prose">{group.description || 'No description yet.'}</div>

      <dl className="facts">
        <div>
          <dt>When</dt>
          <dd>{group.meeting_time || 'To be decided'}</dd>
        </div>
        <div>
          <dt>Where</dt>
          <dd>{group.location || 'To be decided'}</dd>
        </div>
        <div>
          <dt>Capacity</dt>
          <dd>{group.capacity} students</dd>
        </div>
      </dl>

      <section>
        <h2>Members ({group.members.length})</h2>
        <ul className="members">
          {group.members.map((member) => (
            <li key={member.id}>
              @{member.username}
              {member.id === group.owner.id && <span className="badge">owner</span>}
            </li>
          ))}
        </ul>
      </section>
    </article>
  )
}
