import { useState, useEffect, useContext } from 'react';
import { toast } from 'react-toastify';
import { AuthContext } from '../App';

interface FoodItem {
  _id: string;
  name: string;
  description: string;
  price: number;
  category: string;
}

export default function Home() {
  const [foods, setFoods] = useState<FoodItem[]>([]);
  const { user, setShowAuthModal, setCartCount } = useContext(AuthContext);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:7777';

  useEffect(() => {
    fetch(`${API_URL}/api/food`)
      .then(res => res.json())
      .then(data => setFoods(data))
      .catch(err => toast.error('Failed to load menu'));
  }, []);

  const handleAddToCart = async (food: FoodItem) => {
    if (!user) {
      setShowAuthModal(true);
      return;
    }

    try {
      // Fetch current cart
      const res = await fetch(`${API_URL}/api/cart`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      });
      let cart = [];
      if (res.ok) {
        cart = await res.json();
      }

      // Add or update quantity
      const existingItem = cart.find((item: any) => item.foodItemId._id === food._id || item.foodItemId === food._id);
      if (existingItem) {
        existingItem.quantity += 1;
      } else {
        cart.push({ foodItemId: food._id, quantity: 1 });
      }

      // Save cart
      const updateRes = await fetch(`${API_URL}/api/cart`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify({ cart: cart.map((c: any) => ({ foodItemId: c.foodItemId._id || c.foodItemId, quantity: c.quantity })) })
      });

      if (updateRes.ok) {
        setCartCount(cart.reduce((acc: number, val: any) => acc + val.quantity, 0));
        toast.success(`${food.name} added to cart!`);
      }
    } catch (err) {
      toast.error('Failed to add to cart');
    }
  };

  const categories = ['South Indian', 'North Indian', 'Italian', 'Chinese'];

  return (
    <>
      <div className="hero">
        <div className="container">
          <h1>Welcome to Hotel Fiesta</h1>
          <p>Experience the finest blend of multi-cuisine delicacies wrapped in vibrant flavors to delight your taste buds!</p>
          <button className="btn" onClick={() => window.scrollTo({ top: document.getElementById('menu')?.offsetTop, behavior: 'smooth' })}>
            Explore Menu
          </button>
        </div>
      </div>

      <div id="menu" className="container">
        {categories.map(category => {
          const categoryFoods = foods.filter(f => f.category === category);
          if (categoryFoods.length === 0) return null;
          return (
            <div key={category}>
              <h2 className="category-title">{category} Delights</h2>
              <div className="food-grid">
                {categoryFoods.map(food => (
                  <div key={food._id} className="food-card">
                    <h3>{food.name}</h3>
                    <p>{food.description}</p>
                    <span className="food-price">₹{food.price}</span>
                    <button className="btn btn-secondary" onClick={() => handleAddToCart(food)}>
                      Add to Cart
                    </button>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
