<script>
  import { onMount } from 'svelte';
  import { link } from 'svelte-spa-router';
  import { isAuthenticated } from '../lib/auth.js';

  let messages = [
    {
      id: 1,
      type: 'system',
      content: 'Welcome to AI Assistant. How can I help you today?',
      timestamp: new Date(Date.now() - 60000)
    }
  ];

  let userInput = '';
  let chatContainer;
  let messagesContainer;

  function scrollToBottom() {
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  function sendMessage() {
    if (!userInput.trim()) return;

    // Add user message
    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      content: userInput,
      timestamp: new Date()
    };
    
    messages = [...messages, userMessage];
    
    // Clear input
    userInput = '';
    
    // Scroll to bottom after rendering user message
    setTimeout(scrollToBottom, 0);
    
    // Simulate AI response after a delay
    setTimeout(() => {
      const aiResponse = generateAIResponse(userMessage.content);
      messages = [...messages, {
        id: messages.length + 1,
        type: 'system',
        content: aiResponse,
        timestamp: new Date()
      }];
      
      // Scroll to bottom after rendering AI response
      setTimeout(scrollToBottom, 0);
    }, 1000);
  }

  function generateAIResponse(userQuery) {
    // Mock AI response based on user query
    const responses = {
      'hello': 'Hello! How can I assist you today?',
      'help': 'I can help you with document summaries, answer questions about the system, or provide guidance on AI competency evaluation.',
      'document': 'Which document would you like me to summarize or provide information about?',
      'summarize': 'I can summarize documents for you. Please specify which document you would like me to summarize.',
      'document 1': 'Document 1 contains information about AI competency evaluation procedures. It outlines metrics for measuring performance including accuracy, response time, and knowledge breadth.',
      'document 2': 'Document 2 describes implementation strategies for AI systems in various organizational contexts, including best practices for deployment and integration.',
      'document 3': 'Document 3 provides case studies of successful AI implementations with detailed analysis of outcomes and lessons learned.',
      'permissions': 'User permissions are managed by administrators. There are different access levels for documents and chat functionality.',
    };
    
    // Check if query contains any keywords
    const lowerQuery = userQuery.toLowerCase();
    for (const [keyword, response] of Object.entries(responses)) {
      if (lowerQuery.includes(keyword)) {
        return response;
      }
    }
    
    // Default response
    return "I'm not sure I understand your question. Could you please rephrase or provide more details?";
  }

  function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  onMount(() => {
    scrollToBottom();
  });
</script>

<div class="chat-page">
  <div class="header">
    <h1>AI Chat Assistant</h1>
    <a href="#/console" use:link class="back-link">← Back to Console</a>
  </div>

  <div class="chat-container" bind:this={chatContainer}>
    <div class="chat-messages" bind:this={messagesContainer}>
      {#each messages as message (message.id)}
        <div class={`message ${message.type}`}>
          <div class="message-content">{message.content}</div>
          <div class="message-time">{message.timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
        </div>
      {/each}
    </div>
    
    <div class="chat-input">
      <textarea 
        placeholder="Type your message here..."
        bind:value={userInput}
        on:keydown={handleKeydown}
      ></textarea>
      <button class="send-button" on:click={sendMessage}>Send</button>
    </div>
  </div>
</div>

<style>
  .chat-page {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  h1 {
    margin: 0;
    color: #2d3748;
  }

  .back-link {
    color: #4299e1;
    text-decoration: none;
  }

  .chat-container {
    display: flex;
    flex-direction: column;
    height: 80vh;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .chat-messages {
    flex: 1;
    padding: 1rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    background-color: #f7fafc;
  }

  .message {
    max-width: 80%;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    position: relative;
  }

  .message.system {
    align-self: flex-start;
    background-color: #e2e8f0;
    color: #2d3748;
  }

  .message.user {
    align-self: flex-end;
    background-color: #4299e1;
    color: white;
  }

  .message-time {
    font-size: 0.75rem;
    margin-top: 0.25rem;
    opacity: 0.7;
    text-align: right;
  }

  .chat-input {
    display: flex;
    padding: 1rem;
    background-color: #edf2f7;
    border-top: 1px solid #e2e8f0;
  }

  .chat-input textarea {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    resize: none;
    height: 40px;
    font-family: inherit;
  }

  .send-button {
    margin-left: 0.5rem;
    background-color: #4299e1;
    color: white;
    border: none;
    padding: 0 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
  }
</style>
