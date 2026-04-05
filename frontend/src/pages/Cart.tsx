import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { AuthContext } from '../App';

export default function Cart() {
  const [cart, setCart] = useState<any[]>([]);
  const { user, setShowAuthModal, setCartCount } = useContext(AuthContext);
  const navigate = useNavigate();

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:7777';

  useEffect(() => {
    if (!user) {
      setShowAuthModal(true);
      return;
    }
    fetchCart();
  }, [user]);

  const fetchCart = async () => {
    try {
      const res = await fetch(`${API_URL}/api/cart`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCart(data);
        setCartCount(data.reduce((acc: number, val: any) => acc + val.quantity, 0));
      }
    } catch (err) {
      toast.error('Failed to load cart');
    }
  };

  const total = cart.reduce((acc, item) => {
    return acc + ((item.foodItemId?.price || 0) * item.quantity);
  }, 0);

  if (!user) {
    return (
      <div className="container" style={{ textAlign: 'center', marginTop: '100px' }}>
        <h2>Please login to view your cart</h2>
      </div>
    );
  }

  return (
    <div className="container cart-wrap">
      <h2 style={{ marginBottom: '30px', color: 'var(--primary-color)' }}>Your Cart</h2>
      {cart.length === 0 ? (
        <p>Your cart is empty. Go add some delicious food!</p>
      ) : (
        <>
          <div style={{ background: 'var(--card-bg)', borderRadius: '12px', padding: '20px', boxShadow: 'var(--shadow)' }}>
            {cart.map((item, index) => (
              <div key={index} className="cart-item">
                <div>
                  <h4 style={{ fontSize: '1.2rem' }}>{item.foodItemId?.name}</h4>
                  <p style={{ color: '#666' }}>Quantity: {item.quantity}</p>
                </div>
                <div style={{ fontWeight: 'bold' }}>
                  ₹{(item.foodItemId?.price || 0) * item.quantity}
                </div>
              </div>
            ))}
          </div>
          <div className="cart-total">
            Total: ₹{total}
          </div>
          <div style={{ textAlign: 'right' }}>
            <button className="btn" onClick={() => navigate('/payment')}>
              Proceed to Payment
            </button>
          </div>
        </>
      )}
    </div>
  );
}
