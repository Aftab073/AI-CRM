import React, { useState } from 'react';
import './styles.css';

const LogInteractionScreen = () => {
  const initialFormState = {
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

  const [formState, setFormState] = useState(initialFormState);
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormState((prevState) => ({
      ...prevState,
      [name]: value,
    }));
  };

  const handleChatSubmit = async () => {
    if (!chatInput.trim()) return;
    const userMessage = { sender: 'user', text: chatInput };
    setChatHistory((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setChatInput('');

    try {
      const response = await fetch('http://localhost:8000/api/ai_extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: chatInput }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'AI processing failed.');
      }
      
      const extractedData = await response.json();
      setChatHistory((prev) => [...prev, { sender: 'bot', text: 'Details extracted. Please review the form and save.' }]);

      const newState = { ...initialFormState, interaction_date: formState.interaction_date };
      for (const key in extractedData) {
          if (extractedData[key] !== null && extractedData[key] !== undefined) {
              newState[key] = extractedData[key];
          }
      }
      setFormState(newState);

    } catch (error) {
      const errorMessage = { sender: 'bot', text: `Error: ${error.message}` };
      setChatHistory((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    // --- FIX: Sanitize the data before sending ---
    // Create a copy of the state to modify
    const payload = { ...formState };

    // Loop over the keys and convert empty strings to null for optional fields
    for (const key in payload) {
      if (payload[key] === '') {
        // Exclude required fields like hcp_name from this logic if necessary,
        // but for our optional fields, this is safe.
        if (key === 'interaction_time' || key === 'attendees' || key === 'topics_discussed' || key === 'materials_shared' || key === 'outcomes' || key === 'follow_up_actions') {
           payload[key] = null;
        }
      }
    }

    try {
      const response = await fetch('http://localhost:8000/api/interactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload), // Send the sanitized payload
      });

       if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`(${response.status}) ${errorData.detail}` || 'Failed to save interaction.');
      }

      const savedInteraction = await response.json();
      const successMessage = { sender: 'bot', text: `Success! Interaction ID ${savedInteraction.id} has been saved.` };
      setChatHistory((prev) => [...prev, successMessage]);
      setFormState(initialFormState);

    } catch (error) {
      const errorMessage = { sender: 'bot', text: `Save Failed: ${error.message}` };
      setChatHistory((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="container">
      <header className="header">
        <h1>Log HCP Interaction</h1>
        <p>Use the AI Assistant to pre-fill the form, then review and save.</p>
      </header>
      <main className="main-content">
        <div className="form-container">
          <h2>Interaction Details (Review & Confirm)</h2>
          <form onSubmit={handleFormSubmit}>
            <div className="form-grid">
              <div className="form-field"><label>HCP Name</label><input type="text" name="hcp_name" value={formState.hcp_name} onChange={handleInputChange} required /></div>
              <div className="form-field"><label>Interaction Type</label><select name="interaction_type" value={formState.interaction_type} onChange={handleInputChange}><option>Scheduled Visit</option><option>Unscheduled Visit</option><option>Phone Call</option><option>Email</option><option>Conference</option></select></div>
              <div className="form-field"><label>Date</label><input type="date" name="interaction_date" value={formState.interaction_date} onChange={handleInputChange} /></div>
              <div className="form-field"><label>Time</label><input type="time" name="interaction_time" value={formState.interaction_time} onChange={handleInputChange} /></div>
            </div>
            <div className="form-field"><label>Attendees</label><input type="text" name="attendees" value={formState.attendees} onChange={handleInputChange} /></div>
            <div className="form-field"><label>Topics Discussed</label><textarea name="topics_discussed" value={formState.topics_discussed} onChange={handleInputChange}></textarea></div>
            <div className="form-field"><label>Materials Shared / Samples Distributed</label><textarea name="materials_shared" value={formState.materials_shared} onChange={handleInputChange}></textarea></div>
            <div className="form-field"><label>Observed/Inferred HCP Sentiment</label><select name="observed_sentiment" value={formState.observed_sentiment} onChange={handleInputChange}><option>Positive</option><option>Neutral</option><option>Negative</option><option>Inquisitive</option></select></div>
            <div className="form-field"><label>Outcomes</label><textarea name="outcomes" value={formState.outcomes} onChange={handleInputChange}></textarea></div>
            <div className="form-field"><label>Follow-up Actions</label><textarea name="follow_up_actions" value={formState.follow_up_actions} onChange={handleInputChange}></textarea></div>
            <button type="submit" className="submit-button" disabled={isLoading || !formState.hcp_name}>
              {isLoading ? 'Processing...' : 'Confirm & Save Interaction'}
            </button>
          </form>
        </div>
        <div className="ai-container">
            <h2>AI Assistant</h2>
            <div className="chat-window"><div className="chat-message bot">Log your interaction in one go. The form will be populated for your review.</div>{chatHistory.map((msg, index) => (<div key={index} className={`chat-message ${msg.sender}`}>{msg.text}</div>))}{isLoading && <div className="chat-message bot loading"><span></span><span></span><span></span></div>}</div>
            <div className="chat-input-area"><input type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && handleChatSubmit()} placeholder="Log interaction details here..." disabled={isLoading}/><button onClick={handleChatSubmit} disabled={isLoading || !chatInput.trim()}>{isLoading ? '...' : 'Log'}</button></div>
        </div>
      </main>
    </div>
  );
};

export default LogInteractionScreen;