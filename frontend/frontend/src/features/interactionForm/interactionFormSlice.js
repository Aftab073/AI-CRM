import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  hcp_name: '',
  interaction_type: 'Scheduled Visit',
  interaction_date: new Date().toISOString().split('T')[0],
  interaction_time: '',
  attendees: '',
  topics_discussed: '',
  materials_shared: '',
  observed_sentiment: 'Neutral',
  outcomes: '',
  follow_up_actions: '',
};

export const interactionFormSlice = createSlice({
  name: 'interactionForm',
  initialState,
  reducers: {
    updateField: (state, action) => {
      const { name, value } = action.payload;
      state[name] = value;
    },
    resetForm: (state) => {
      return initialState;
    },
    // --- THIS IS THE DEFINITIVE, CORRECTED LOGIC ---
    populateForm: (state, action) => {
      // The `action.payload` is the complete data object from the AI.
      // This simple logic correctly merges the AI data over the initial state,
      // ensuring all fields are populated correctly.
      const newState = { ...initialState, ...action.payload };
      return newState;
    },
  },
});

export const { updateField, resetForm, populateForm } = interactionFormSlice.actions;

export const selectForm = (state) => state.interactionForm;

export default interactionFormSlice.reducer;