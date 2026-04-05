import mongoose from 'mongoose';

const userSchema = new mongoose.Schema({
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true },
  cart: [{
    foodItemId: { type: mongoose.Schema.Types.ObjectId, ref: 'FoodItem' },
    quantity: { type: Number, default: 1 }
  }]
}, { timestamps: true });

export const User = mongoose.models.User || mongoose.model('User', userSchema);
