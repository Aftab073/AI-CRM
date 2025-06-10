import { configureStore } from '@reduxjs/toolkit';
import interactionFormReducer from '../features/interactionForm/interactionFormSlice';

export const store = configureStore({
  reducer: {
    interactionForm: interactionFormReducer,
  },
});