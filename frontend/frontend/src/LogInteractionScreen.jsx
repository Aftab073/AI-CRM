import React, { useState, useEffect } from 'react';
import './styles.css';

const LogInteractionScreen = () => {
  const initialFormState = {
    hcp_name: '',
    interaction_type: 'Scheduled Visit',
    interaction_date: new Date().toISOString().split('T')[0],
    interaction_time: '', // Set default time to empty
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

  // The form submit handler is removed as it's not part of the core AI flow for this final version.
  // You can add it back if you need dual-mode entry.

  const handleChatSubmit = async () => {
    if (!chatInput.trim()) return;

    const userMessage = { sender: 'user', text: chatInput };
    setChatHistory((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setChatInput('');

    try {
      const response = await fetch('http://localhost:8000/api/chat_interaction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: chatInput }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'AI processing failed.');
      }
      
      const extractedData = await response.json();
      
      const botMessage = { sender: 'bot', text: 'Interaction details extracted and populated in the form.' };
      setChatHistory((prev) => [...prev, botMessage]);

      // --- DEFINITIVE STATE UPDATE LOGIC ---
      // 1. Start with a fresh, clean copy of the initial state.
      const newState = { ...initialFormState };
      
      // 2. Merge the data from the AI over the clean state.
      // This ensures any field not returned by the AI (because it was null) is reset.
      for (const key in extractedData) {
          if (extractedData[key] !== null && extractedData[key] !== undefined) {
              newState[key] = extractedData[key];
          }
      }
      
      // 3. Set the final, clean state.
      setFormState(newState);

    } catch (error) {
      console.error('Error with AI chat:', error);
      const errorMessage = { sender: 'bot', text: `Error: ${error.message}` };
      setChatHistory((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container">
      <header className="header">
        <h1>Log HCP Interaction</h1>
        <p>Use the AI Assistant to log your interaction in a single step.</p>
      </header>
      <main className="main-content">
        {/* Left Side: Structured Form */}
        <div className="form-container">
          <h2>Interaction Details (Review & Confirm)</h2>
          <form onSubmit={(e) => { e.preventDefault(); alert('Data ready for submission!'); }}>
            <div className="form-grid">
              <div className="form-field">
                <label>HCP Name</label>
                <input type="text" name="hcp_name" value={formState.hcp_name} onChange={handleInputChange} required />
              </div>
              <div className="form-field">
                <label>Interaction Type</label>
                <select name="interaction_type" value={formState.interaction_type} onChange={handleInputChange}>
                  <option>Scheduled Visit</option>
                  <option>Unscheduled Visit</option>
                  <option>Phone Call</option>
                  <option>Email</option>
                  <option>Conference</option>
                </select>
              </div>
              <div className="form-field">
                <label>Date</label>
                <input type="date" name="interaction_date" value={formState.interaction_date} onChange={handleInputChange} />
              </div>
              <div className="form-field">
                <label>Time</label>
                <input type="time" name="interaction_time" value={formState.interaction_time} onChange={handleInputChange} />
              </div>
            </div>
            <div className="form-field">
              <label>Attendees</label>
              <input type="text" name="attendees" value={formState.attendees} onChange={handleInputChange} />
            </div>
            <div className="form-field">
              <label>Topics Discussed</label>
              <textarea name="topics_discussed" value={formState.topics_discussed} onChange={handleInputChange}></textarea>
            </div>
             <div className="form-field">
              <label>Materials Shared / Samples Distributed</label>
              <textarea name="materials_shared" value={formState.materials_shared} onChange={handleInputChange}></textarea>
            </div>
            <div className="form-field">
              <label>Observed/Inferred HCP Sentiment</label>
              <select name="observed_sentiment" value={formState.observed_sentiment} onChange={handleInputChange}>
                <option>Positive</option>
                <option>Neutral</option>
                <option>Negative</option>
                <option>Inquisitive</option>
              </select>
            </div>
            <div className="form-field">
              <label>Outcomes</label>
              <textarea name="outcomes" value={formState.outcomes} onChange={handleInputChange}></textarea>
            </div>
            <div className="form-field">
              <label>Follow-up Actions</label>
              <textarea name="follow_up_actions" value={formState.follow_up_actions} onChange={handleInputChange}></textarea>
            </div>
            <button type="submit" className="submit-button" disabled={isLoading}>
              Confirm & Save Interaction
            </button>
          </form>
        </div>

        {/* Right Side: AI Assistant */}
        <div className="ai-container">
          <h2>AI Assistant</h2>
          <div className="chat-window">
            <div className="chat-message bot">
              Log your interaction in one go. For example: "Spoke with Dr. Carter on the phone at 4:30 PM today about the new trial data. She seemed positive. I sent her the PDF brochure."
            </div>
            {chatHistory.map((msg, index) => (
              <div key={index} className={`chat-message ${msg.sender}`}>
                {msg.text}
              </div>
            ))}
             {isLoading && <div className="chat-message bot loading"><span></span><span></span><span></span></div>}
          </div>
          <div className="chat-input-area">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleChatSubmit()}
              placeholder="Log interaction details here..."
              disabled={isLoading}
            />
            <button onClick={handleChatSubmit} disabled={isLoading || !chatInput.trim()}>
              {isLoading ? '...' : 'Log'}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default LogInteractionScreen;