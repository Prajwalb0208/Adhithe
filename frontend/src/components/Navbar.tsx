import { useContext } from 'react';
import { Link } from 'react-router-dom';
import { AuthContext } from '../App';

export default function Navbar() {
  const { user, setShowAuthModal, logout, cartCount } = useContext(AuthContext);

  return (
    <nav className="navbar">
      <div className="container">
        <Link to="/" className="logo">🏨 Hotel Fiesta</Link>
        <div className="nav-links">
          <Link to="/">Home</Link>
          <Link to="/cart">Cart {cartCount > 0 && `(${cartCount})`}</Link>
          {user ? (
            <>
              <span style={{ fontWeight: 600 }}>{user.email}</span>
              <button 
                onClick={logout} 
                className="btn btn-secondary"
                style={{ padding: '6px 15px', fontSize: '0.9rem' }}
              >
                Logout
              </button>
            </>
          ) : (
            <button 
              onClick={() => setShowAuthModal(true)} 
              className="btn"
              style={{ padding: '6px 15px', fontSize: '0.9rem' }}
            >
              Login
            </button>
          )}
        </div>
      </div>
    </nav>
  );
}
