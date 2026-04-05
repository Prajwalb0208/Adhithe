import { Link } from 'react-router-dom';

export default function Success() {
  return (
    <div className="container" style={{ textAlign: 'center', marginTop: '100px' }}>
      <div style={{ background: 'var(--card-bg)', padding: '60px', borderRadius: '20px', boxShadow: 'var(--shadow)', maxWidth: '600px', margin: '0 auto' }}>
        <div style={{ fontSize: '5rem', marginBottom: '20px' }}>✅</div>
        <h1 style={{ color: 'var(--secondary-color)', marginBottom: '20px' }}>Payment Successful!</h1>
        <p style={{ color: '#666', marginBottom: '40px', fontSize: '1.2rem' }}>
          Your order has been placed successfully. Get ready for a delicious feast!
        </p>
        <Link to="/" className="btn">
          Back to Home
        </Link>
      </div>
    </div>
  );
}
