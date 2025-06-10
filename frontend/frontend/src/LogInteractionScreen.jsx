import React, { useState } from 'react';
// Import Redux hooks and actions
import { useDispatch, useSelector } from 'react-redux';
import { updateField, resetForm, selectForm, populateForm } from './features/interactionForm/interactionFormSlice';

const LogInteractionScreen = () => {
  // --- STATE MANAGEMENT ---
  // The form's state is now read directly from the Redux store
  const formState = useSelector(selectForm);
  // The dispatch function is used to send actions to the Redux store
  const dispatch = useDispatch();

  // Local component state is still used for UI elements not part of the form, like the chat
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);


  // --- HANDLER FUNCTIONS ---

  // Dispatches an action to update a single field in the Redux store
  const handleInputChange = (e) => {
    dispatch(updateField({ name: e.target.name, value: e.target.value }));
  };

  // Handles the AI submission
  const handleChatSubmit = async () => {
    if (!chatInput.trim()) return;
    const userMessage = { sender: 'user', text: chatInput };
    setChatHistory((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setChatInput('');

    try {
      const response = await fetch('http://localhost:8000/api/ai_extract', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: chatInput }),
      });
      if (!response.ok) {
        const errorData = await response.json(); throw new Error(errorData.detail || 'AI processing failed.');
      }
      const extractedData = await response.json();
      setChatHistory((prev) => [...prev, { sender: 'bot', text: 'Details extracted. Please review the form and save.' }]);
      
      // Dispatch an action to populate the form in the Redux store
      dispatch(populateForm(extractedData));

    } catch (error) {
      setChatHistory((prev) => [...prev, { sender: 'bot', text: `Error: ${error.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handles the final form submission to the database
  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    const payload = { ...formState };
    for (const key in payload) {
      if (payload[key] === '') {
        if (['interaction_time', 'attendees', 'topics_discussed', 'materials_shared', 'outcomes', 'follow_up_actions'].includes(key)) {
           payload[key] = null;
        }
      }
    }
    try {
      const response = await fetch('http://localhost:8000/api/interactions', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const errorData = await response.json(); throw new Error(`(${response.status}) ${errorData.detail}` || 'Failed to save interaction.');
      }
      const savedInteraction = await response.json();
      alert(`Success! Interaction ID ${savedInteraction.id} has been saved.`);
      
      // Dispatch an action to reset the form in the Redux store
      dispatch(resetForm());
      setChatHistory([]);

    } catch (error) {
      alert(`Save failed: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Reusable Tailwind classes for a consistent, professional look
  const inputClasses = "block w-full px-3 py-2 bg-white border border-slate-300 rounded-md text-sm shadow-sm placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition";
  const labelClasses = "block text-sm font-medium text-slate-700 mb-1";

  return (
    // Applying the Inter font via `font-sans` and a soft background color
    <div className="bg-slate-50 min-h-screen font-sans">
      <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
        
        <header className="text-center mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight">Log HCP Interaction</h1>
          <p className="mt-2 text-base sm:text-lg text-slate-600">Use the AI Assistant to pre-fill the form, then review and save.</p>
        </header>
        
        {/* Responsive Grid for the two-column layout */}
        <main className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          
          {/* Form Container */}
          <div className="lg:col-span-3 bg-white rounded-2xl shadow-xl p-6 lg:p-8">
            <h2 className="text-xl font-semibold text-slate-900 border-b border-slate-200 pb-4 mb-6">Interaction Details (Review & Confirm)</h2>
            <form onSubmit={handleFormSubmit} className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div><label htmlFor="hcp_name" className={labelClasses}>HCP Name</label><input id="hcp_name" type="text" name="hcp_name" value={formState.hcp_name} onChange={handleInputChange} className={inputClasses} required /></div>
                <div><label htmlFor="interaction_type" className={labelClasses}>Interaction Type</label><select id="interaction_type" name="interaction_type" value={formState.interaction_type} onChange={handleInputChange} className={inputClasses}><option>Scheduled Visit</option><option>Unscheduled Visit</option><option>Phone Call</option><option>Email</option><option>Conference</option></select></div>
                <div><label htmlFor="interaction_date" className={labelClasses}>Date</label><input id="interaction_date" type="date" name="interaction_date" value={formState.interaction_date} onChange={handleInputChange} className={inputClasses} /></div>
                <div><label htmlFor="interaction_time" className={labelClasses}>Time</label><input id="interaction_time" type="time" name="interaction_time" value={formState.interaction_time} onChange={handleInputChange} className={inputClasses} /></div>
              </div>
              <div><label htmlFor="attendees" className={labelClasses}>Attendees</label><input id="attendees" type="text" name="attendees" value={formState.attendees} onChange={handleInputChange} className={inputClasses} /></div>
              <div><label htmlFor="topics_discussed" className={labelClasses}>Topics Discussed</label><textarea id="topics_discussed" name="topics_discussed" rows="3" value={formState.topics_discussed} onChange={handleInputChange} className={inputClasses}></textarea></div>
              <div><label htmlFor="materials_shared" className={labelClasses}>Materials Shared / Samples Distributed</label><textarea id="materials_shared" name="materials_shared" rows="3" value={formState.materials_shared} onChange={handleInputChange} className={inputClasses}></textarea></div>
              <div><label htmlFor="observed_sentiment" className={labelClasses}>Observed/Inferred HCP Sentiment</label><select id="observed_sentiment" name="observed_sentiment" value={formState.observed_sentiment} onChange={handleInputChange} className={inputClasses}><option>Positive</option><option>Neutral</option><option>Negative</option><option>Inquisitive</option></select></div>
              <div><label htmlFor="outcomes" className={labelClasses}>Outcomes</label><textarea id="outcomes" name="outcomes" rows="2" value={formState.outcomes} onChange={handleInputChange} className={inputClasses}></textarea></div>
              <div><label htmlFor="follow_up_actions" className={labelClasses}>Follow-up Actions</label><textarea id="follow_up_actions" name="follow_up_actions" rows="2" value={formState.follow_up_actions} onChange={handleInputChange} className={inputClasses}></textarea></div>
              <button type="submit" className="w-full bg-indigo-600 text-white font-bold py-3 px-4 rounded-lg shadow-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-slate-400 disabled:cursor-not-allowed transition-all duration-300" disabled={isLoading || !formState.hcp_name}>
                {isLoading ? 'Processing...' : 'Confirm & Save Interaction'}
              </button>
            </form>
          </div>

          {/* AI Assistant Container */}
          <div className="lg:col-span-2 bg-white rounded-2xl shadow-xl p-6 lg:p-8 flex flex-col">
            <h2 className="text-xl font-semibold text-slate-900 border-b border-slate-200 pb-4 mb-6">AI Assistant</h2>
            <div className="flex-grow bg-slate-50 rounded-lg p-4 overflow-y-auto h-96 space-y-4">
              <div className="p-3 rounded-lg bg-indigo-100 text-indigo-800 text-sm shadow-sm">Log your interaction in one go. The form will be populated for your review.</div>
              {chatHistory.map((msg, index) => (
                <div key={index} className={`w-fit max-w-xs md:max-w-sm rounded-xl px-4 py-2 shadow-sm ${msg.sender === 'user' ? 'bg-indigo-600 text-white ml-auto' : 'bg-slate-200 text-slate-800'}`}>
                  {msg.text}
                </div>
              ))}
              {isLoading && <div className="p-3"><div className="w-fit max-w-sm rounded-xl px-4 py-3 bg-slate-200 text-slate-800 flex items-center space-x-2"> <div className="w-2 h-2 bg-slate-500 rounded-full animate-pulse"></div> <div className="w-2 h-2 bg-slate-500 rounded-full animate-pulse [animation-delay:0.2s]"></div> <div className="w-2 h-2 bg-slate-500 rounded-full animate-pulse [animation-delay:0.4s]"></div> </div></div>}
            </div>
            <div className="mt-6 flex gap-3">
              <input type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && handleChatSubmit()} placeholder="Log interaction details here..." disabled={isLoading} className={`${inputClasses} flex-grow`}/>
              <button onClick={handleChatSubmit} disabled={isLoading || !chatInput.trim()} className="bg-indigo-600 text-white font-bold py-2 px-5 rounded-lg shadow-md hover:bg-indigo-700 disabled:bg-slate-400 disabled:cursor-not-allowed transition-all duration-300">
                Log
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default LogInteractionScreen;