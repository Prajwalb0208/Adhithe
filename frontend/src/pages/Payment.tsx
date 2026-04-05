import { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { AuthContext } from '../App';

export default function Payment() {
  const [loading, setLoading] = useState(false);
  const { user, setCartCount } = useContext(AuthContext);
  const navigate = useNavigate();

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:7777';

  const handlePaymentMock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    
    setLoading(true);
    try {
      // Mock payment delay
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      const res = await fetch(`${API_URL}/api/payment`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.token}`
        }
      });
      
      if (res.ok) {
        setCartCount(0);
        navigate('/success');
      } else {
        toast.error('Payment failed');
      }
    } catch (err) {
      toast.error('Network error during payment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ maxWidth: '500px', marginTop: '60px' }}>
      <div style={{ background: 'var(--card-bg)', padding: '40px', borderRadius: '12px', boxShadow: 'var(--shadow)' }}>
        <h2 style={{ textAlign: 'center', marginBottom: '30px', color: 'var(--primary-color)' }}>
          Checkout Payment
        </h2>
        
        <form onSubmit={handlePaymentMock}>
          <div className="form-group">
            <label>Card Number</label>
            <input type="text" placeholder="1234 5678 9101 1121" required />
          </div>
          <div style={{ display: 'flex', gap: '20px' }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Expiry (MM/YY)</label>
              <input type="text" placeholder="12/25" required />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>CVV</label>
              <input type="password" placeholder="123" required />
            </div>
          </div>
          <div className="form-group" style={{ marginBottom: '30px' }}>
            <label>Cardholder Name</label>
            <input type="text" placeholder="John Doe" required />
          </div>
          
          <button type="submit" className="btn btn-secondary" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Processing...' : 'Pay Now'}
          </button>
        </form>
      </div>
    </div>
  );
}
