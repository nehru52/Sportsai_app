// AI COACH CHAT FUNCTIONALITY

let questionsAsked = 0;
const MAX_FREE_QUESTIONS = 3;

// Sample AI responses based on keywords
const aiResponses = {
  'entry phase': "Your entry phase needs work. Elite athletes drop their hips to 0.63m at contact — you're at 0.74m. Try this drill: 50 penetration steps focusing on driving your hips DOWN and FORWARD. Feel like you're shooting under a table.",
  
  'spike': "Looking at your spike data, your approach timing is solid but your arm swing is late by 0.12 seconds. This costs you 8-12% power. Drill: 30 approach jumps with exaggerated early arm load. Feel the arm cocking BEFORE you leave the ground.",
  
  'serve': "Your serve toss is inconsistent — varies by 0.3m between serves. Elite servers have <0.1m variance. Drill: 100 tosses without hitting, mark your target spot on the floor. Toss should land in a dinner-plate sized circle every time.",
  
  'block': "Your block timing is 0.15s early — you're landing before the hitter contacts. This is common. Drill: Watch the hitter's shoulder, not the ball. Jump when their hitting shoulder starts forward, not when the ball leaves the setter's hands.",
  
  'improve': "Based on your last 5 sessions, focus on: 1) Hip height at entry (biggest gap vs elite), 2) Arm swing timing (costing you power), 3) Consistency (your variance is 2x higher than it should be). Work on drill #1 this week.",
  
  'week': "This week, prioritize your entry phase. You've improved 8% in the last month, but you're plateauing. The hip drive penetration drill will break through this. Do it 3x this week, 50 reps each. Upload videos so I can track progress.",
  
  'beat': "Against bigger opponents, technique beats size. Your entry phase is your weapon — if you can get lower and faster, size doesn't matter. Focus on: 1) Explosive first step, 2) Hip drive under their center of gravity, 3) Hand control. You're 62nd percentile now, targeting 75th in 4 weeks.",
  
  'last 5': "Last 5 sessions analysis:\n\nSession 1: 68/100 - Entry phase weak\nSession 2: 72/100 - Improved hip drive\nSession 3: 70/100 - Inconsistent timing\nSession 4: 74/100 - Best execution phase yet\nSession 5: 72/100 - Solid overall\n\nTrend: +6% improvement. Your execution phase is now above average. Entry phase is the bottleneck. One focused week on hip drive could push you to 78+.",
  
  'default': "Great question! Based on your recent sessions, I'd recommend focusing on consistency first. Your technique variance is higher than it should be. This means some reps are elite-level, others are beginner. Narrowing that gap will boost your average score by 8-12 points. Want specific drills for this?"
};

function sendMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  
  if (!message) return;
  
  // Check question limit
  if (questionsAsked >= MAX_FREE_QUESTIONS) {
    showUpgradeModal();
    return;
  }
  
  // Add user message
  addMessage(message, 'user');
  input.value = '';
  
  // Show typing indicator
  showTypingIndicator();
  
  // Simulate AI response delay
  setTimeout(() => {
    hideTypingIndicator();
    const response = getAIResponse(message);
    addMessage(response, 'ai');
    questionsAsked++;
    updateQuestionsRemaining();
  }, 1500 + Math.random() * 1000);
}

function sendQuickPrompt(button) {
  const message = button.textContent.trim();
  document.getElementById('chatInput').value = message;
  sendMessage();
  
  // Hide quick prompts after first use
  document.getElementById('quickPrompts').style.display = 'none';
}

function addMessage(text, sender) {
  const messagesContainer = document.getElementById('chatMessages');
  
  const messageGroup = document.createElement('div');
  messageGroup.className = `message-group ${sender}`;
  
  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = sender === 'ai' ? '🤖' : '👤';
  
  const content = document.createElement('div');
  content.className = 'message-content';
  
  if (sender === 'ai') {
    const label = document.createElement('div');
    label.className = 'message-label';
    label.textContent = 'AI COACH · your data';
    content.appendChild(label);
  }
  
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  
  // Handle multi-line responses
  const paragraphs = text.split('\n\n');
  paragraphs.forEach((para, index) => {
    const p = document.createElement('p');
    p.textContent = para;
    bubble.appendChild(p);
  });
  
  const time = document.createElement('div');
  time.className = 'message-time';
  time.textContent = 'Just now';
  
  content.appendChild(bubble);
  content.appendChild(time);
  
  messageGroup.appendChild(avatar);
  messageGroup.appendChild(content);
  
  messagesContainer.appendChild(messageGroup);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showTypingIndicator() {
  const messagesContainer = document.getElementById('chatMessages');
  
  const messageGroup = document.createElement('div');
  messageGroup.className = 'message-group ai';
  messageGroup.id = 'typingIndicator';
  
  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = '🤖';
  
  const content = document.createElement('div');
  content.className = 'message-content';
  
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  
  const indicator = document.createElement('div');
  indicator.className = 'typing-indicator';
  indicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
  
  bubble.appendChild(indicator);
  content.appendChild(bubble);
  messageGroup.appendChild(avatar);
  messageGroup.appendChild(content);
  
  messagesContainer.appendChild(messageGroup);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideTypingIndicator() {
  const indicator = document.getElementById('typingIndicator');
  if (indicator) indicator.remove();
}

function getAIResponse(message) {
  const lowerMessage = message.toLowerCase();
  
  // Check for keywords
  for (const [keyword, response] of Object.entries(aiResponses)) {
    if (lowerMessage.includes(keyword)) {
      return response;
    }
  }
  
  return aiResponses.default;
}

function updateQuestionsRemaining() {
  const remaining = MAX_FREE_QUESTIONS - questionsAsked;
  document.querySelector('.questions-count').textContent = remaining;
  
  if (remaining === 0) {
    document.querySelector('.questions-count').style.color = 'var(--red)';
  } else if (remaining === 1) {
    document.querySelector('.questions-count').style.color = 'var(--gold)';
  }
}

function showUpgradeModal() {
  document.getElementById('upgradeModal').classList.add('show');
}

function closeUpgradeModal() {
  document.getElementById('upgradeModal').classList.remove('show');
}

function handleKeyPress(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

// Close modal on outside click
document.getElementById('upgradeModal')?.addEventListener('click', (e) => {
  if (e.target.id === 'upgradeModal') {
    closeUpgradeModal();
  }
});

// Load questions asked from localStorage
document.addEventListener('DOMContentLoaded', () => {
  const savedQuestions = localStorage.getItem('sportsai_questions_today');
  if (savedQuestions) {
    questionsAsked = parseInt(savedQuestions);
    updateQuestionsRemaining();
  }
  
  // Reset daily at midnight
  const lastReset = localStorage.getItem('sportsai_last_reset');
  const today = new Date().toDateString();
  if (lastReset !== today) {
    questionsAsked = 0;
    localStorage.setItem('sportsai_questions_today', '0');
    localStorage.setItem('sportsai_last_reset', today);
    updateQuestionsRemaining();
  }
});

// Save questions asked
window.addEventListener('beforeunload', () => {
  localStorage.setItem('sportsai_questions_today', questionsAsked.toString());
});
