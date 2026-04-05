import express from 'express';
import mongoose from 'mongoose';
import cors from 'cors';
import dotenv from 'dotenv';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { User } from './models/User.js';
import { FoodItem } from './models/FoodItem.js';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 7777;
const MONGO_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/hotel_management';
const JWT_SECRET = process.env.JWT_SECRET || 'your_jwt_secret_key_here';

// Connect to MongoDB
mongoose.connect(MONGO_URI)
  .then(() => console.log('Connected to MongoDB'))
  .catch((err) => console.error('MongoDB connection error:', err));

// Auth Middleware
const authMiddleware = (req, res, next) => {
  const token = req.header('Authorization')?.replace('Bearer ', '');
  if (!token) return res.status(401).json({ message: 'No token, authorization denied' });

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.userId = decoded.userId;
    next();
  } catch (err) {
    res.status(401).json({ message: 'Token is not valid' });
  }
};

// Routes

// 1. Auth Register
app.post('/api/auth/register', async (req, res) => {
  try {
    const { email, password } = req.body;
    let user = await User.findOne({ email });
    if (user) {
      return res.status(400).json({ message: 'User already exists' });
    }
    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash(password, salt);
    
    user = new User({ email, password: hashedPassword });
    await user.save();
    
    const token = jwt.sign({ userId: user._id }, JWT_SECRET, { expiresIn: '7d' });
    res.status(201).json({ token, user: { email: user.email, _id: user._id } });
  } catch (err) {
    res.status(500).json({ message: 'Server error' });
  }
});

// 2. Auth Login
app.post('/api/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    const user = await User.findOne({ email });
    if (!user) return res.status(400).json({ message: 'Invalid credentials' });
    
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) return res.status(400).json({ message: 'Invalid credentials' });
    
    const token = jwt.sign({ userId: user._id }, JWT_SECRET, { expiresIn: '7d' });
    res.json({ token, user: { email: user.email, _id: user._id } });
  } catch (err) {
    res.status(500).json({ message: 'Server error' });
  }
});

// 3. Get Food Items
app.get('/api/food', async (req, res) => {
  try {
    const foods = await FoodItem.find();
    res.json(foods);
  } catch (err) {
    res.status(500).json({ message: 'Server error' });
  }
});

// 4. Update Cart (Replace old cart)
app.post('/api/cart', authMiddleware, async (req, res) => {
  try {
    const { cart } = req.body; // Array of { foodItemId, quantity }
    const user = await User.findById(req.userId);
    user.cart = cart;
    await user.save();
    res.json({ message: 'Cart updated', cart: user.cart });
  } catch (err) {
    res.status(500).json({ message: 'Server error' });
  }
});

// 5. Get User Cart
app.get('/api/cart', authMiddleware, async (req, res) => {
  try {
    const user = await User.findById(req.userId).populate('cart.foodItemId');
    if (!user) return res.status(404).json({ message: 'User not found' });
    res.json(user.cart);
  } catch (err) {
    res.status(500).json({ message: 'Server error' });
  }
});

// 6. Payment Mockup
app.post('/api/payment', authMiddleware, async (req, res) => {
  try {
    // Mock simple payment functionality
    const user = await User.findById(req.userId);
    // Clear user cart after payment
    user.cart = [];
    await user.save();
    res.json({ message: 'Payment successful', status: 'success' });
  } catch (err) {
    res.status(500).json({ message: 'Server error' });
  }
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
