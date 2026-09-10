import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="brand">
          Study<span>Hub</span>
        </Link>

        <nav className="nav-links">
          <NavLink to="/notes">Notes</NavLink>
          <NavLink to="/groups">Study groups</NavLink>
          {user && <NavLink to="/dashboard">My stuff</NavLink>}
        </nav>

        <div className="nav-actions">
          {user ? (
            <>
              <span className="nav-user">@{user.username}</span>
              <button type="button" className="button ghost" onClick={handleLogout}>
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link className="button ghost" to="/login">
                Sign in
              </Link>
              <Link className="button" to="/register">
                Create account
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
