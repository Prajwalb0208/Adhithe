import mongoose from 'mongoose';
import dotenv from 'dotenv';

// Load env
dotenv.config({ path: '../backend/.env' });

const MONGO_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/hotel_management';

// Inline schema definition to avoid cross-module mongoose instance issues
const foodItemSchema = new mongoose.Schema({
  name: { type: String, required: true },
  description: { type: String, required: true },
  price: { type: Number, required: true },
  category: { 
    type: String, 
    required: true, 
    enum: ['South Indian', 'North Indian', 'Italian', 'Chinese'] 
  },
  imageUrl: { type: String, required: false }
}, { timestamps: true });

const FoodItem = mongoose.models.FoodItem || mongoose.model('FoodItem', foodItemSchema);

const items = [
  { name: 'Idli Sambar', description: 'Soft fluffy idlis with hot sambar', price: 60, category: 'South Indian' },
  { name: 'Masala Dosa', description: 'Crispy dosa with potato filling', price: 90, category: 'South Indian' },
  { name: 'Paneer Butter Masala', description: 'Rich paneer gravy', price: 200, category: 'North Indian' },
  { name: 'Garlic Naan', description: 'Naan topped with garlic', price: 50, category: 'North Indian' },
  { name: 'Margherita Pizza', description: 'Classic cheese and tomato pizza', price: 300, category: 'Italian' },
  { name: 'Pasta Carbonara', description: 'Creamy pasta with herbs', price: 250, category: 'Italian' },
  { name: 'Hakka Noodles', description: 'Stir fried noodles with veggies', price: 150, category: 'Chinese' },
  { name: 'Manchurian Dry', description: 'Crispy veg balls in soy sauce', price: 180, category: 'Chinese' }
];

async function seed() {
  try {
    console.log(`Connecting to ${MONGO_URI}`);
    await mongoose.connect(MONGO_URI);
    console.log('Connected to MongoDB');

    await FoodItem.deleteMany({});
    console.log('Cleared existing food items');

    await FoodItem.insertMany(items);
    console.log('Inserted new food items successfully');

    process.exit(0);
  } catch (error) {
    console.error('Error seeding DB', error);
    process.exit(1);
  }
}

seed();
