import mongoose from 'mongoose';

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

export const FoodItem = mongoose.models.FoodItem || mongoose.model('FoodItem', foodItemSchema);
