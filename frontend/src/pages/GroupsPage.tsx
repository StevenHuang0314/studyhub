import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import GroupCard from '../components/GroupCard'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { Group } from '../types'

export default function GroupsPage() {
  const { user } = useAuth()

  const [groups, setGroups] = useState<Group[]>([])
  const [total, setTotal] = useState(0)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [hasSpace, setHasSpace] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const loadGroups = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.listGroups({
        search: search || undefined,
        has_space: hasSpace || undefined,
      })
      setGroups(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load study groups')
    } finally {
      setLoading(false)
    }
  }, [search, hasSpace])

  useEffect(() => {
    void loadGroups()
  }, [loadGroups])

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Study groups</h1>
          <p className="muted">
            {total} group{total === 1 ? '' : 's'} looking for people.
          </p>
        </div>
        {user && (
          <Link className="button" to="/groups/new">
            Start a group
          </Link>
        )}
      </div>

      <div className="filters">
        <input
          className="grow"
          placeholder="Search by name or description…"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
        />
        <label className="checkbox">
          <input
            type="checkbox"
            checked={hasSpace}
            onChange={(event) => setHasSpace(event.target.checked)}
          />
          Only groups with space
        </label>
      </div>

      {error && <p className="error">{error}</p>}
      {loading ? (
        <p className="muted center">Loading groups…</p>
      ) : groups.length === 0 ? (
        <p className="muted center">No groups match that search.</p>
      ) : (
        <div className="grid">
          {groups.map((group) => (
            <GroupCard key={group.id} group={group} />
          ))}
        </div>
      )}
    </>
  )
}
