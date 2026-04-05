import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Simple global state for demonstration
// In a real app, use Context or Redux
export const AuthContext = React.createContext<any>(null);

import Home from './pages/Home';
import Cart from './pages/Cart';
import Payment from './pages/Payment';
import Success from './pages/Success';
import Navbar from './components/Navbar';
import AuthModal from './components/AuthModal';

function App() {
  const [user, setUser] = useState<{ email: string, token: string } | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [cartCount, setCartCount] = useState(0);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const email = localStorage.getItem('email');
    if (token && email) setUser({ email, token });
  }, []);

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('email');
    setUser(null);
    toast.success('Logged out successfully');
  };

  return (
    <AuthContext.Provider value={{ user, setUser, showAuthModal, setShowAuthModal, cartCount, setCartCount, logout }}>
      <Router>
        <div className="page-wrapper">
          <Navbar />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/cart" element={<Cart />} />
            <Route path="/payment" element={<Payment />} />
            <Route path="/success" element={<Success />} />
          </Routes>
        </div>
        {showAuthModal && <AuthModal onClose={() => setShowAuthModal(false)} />}
        <ToastContainer position="bottom-right" />
      </Router>
    </AuthContext.Provider>
  );
}

export default App;
