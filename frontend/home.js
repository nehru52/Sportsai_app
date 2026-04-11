// HOME PAGE INTERACTIONS

// Animate XP bar on load
document.addEventListener('DOMContentLoaded', () => {
  animateXPBar();
  animateChallengeBar();
  animateScoreRings();
  loadUserData();
});

function animateXPBar() {
  const bar = document.querySelector('.xp-bar-fill');
  if (bar) {
    const targetWidth = bar.style.width;
    bar.style.width = '0%';
    setTimeout(() => {
      bar.style.width = targetWidth;
    }, 300);
  }
}

function animateChallengeBar() {
  const bar = document.querySelector('.challenge-bar-fill');
  if (bar) {
    const targetWidth = bar.style.width;
    bar.style.width = '0%';
    setTimeout(() => {
      bar.style.width = targetWidth;
    }, 500);
  }
}

function animateScoreRings() {
  const rings = document.querySelectorAll('.ring-current, .ring-best, .ring-elite');
  rings.forEach((ring, index) => {
    const offset = ring.getAttribute('stroke-dashoffset');
    ring.setAttribute('stroke-dashoffset', '440');
    setTimeout(() => {
      ring.setAttribute('stroke-dashoffset', offset);
    }, 700 + (index * 200));
  });
}

function loadUserData() {
  // Load from localStorage or API
  const userData = JSON.parse(localStorage.getItem('sportsai_user') || '{}');
  
  if (userData.name) {
    document.querySelector('.athlete-name').textContent = userData.name;
  }
  
  if (userData.xp) {
    updateXP(userData.xp, userData.nextBeltXP || 12000);
  }
  
  if (userData.streak) {
    updateStreak(userData.streak);
  }
}

function updateXP(current, target) {
  const percentage = (current / target) * 100;
  document.querySelector('.xp-label span:first-child').textContent = `${current.toLocaleString()} XP`;
  document.querySelector('.xp-bar-fill').style.width = `${percentage}%`;
}

function updateStreak(days) {
  document.querySelector('.streak-count').textContent = `${days} week streak`;
}

function openProfile() {
  // Navigate to profile page or open modal
  console.log('Opening profile...');
  // For now, just show an alert
  showNotification('Profile feature coming soon!', 'info');
}

function startDrill() {
  showNotification('Starting drill... Upload your video when complete!', 'success');
  setTimeout(() => {
    location.href = 'index.html#uploadSection';
  }, 1500);
}

function showDemo() {
  showNotification('Demo video loading...', 'info');
  // In production, this would open a video modal
}

function viewRivalry() {
  showNotification('Rivalry tracking coming soon!', 'info');
}

function acceptChallenge() {
  showNotification('Challenge accepted! Good luck! 🏆', 'success');
  // Update UI to show accepted state
  event.target.textContent = 'Accepted';
  event.target.style.background = 'var(--green)';
  event.target.style.borderColor = 'var(--green)';
}

// Notification system
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  
  notification.style.cssText = `
    position: fixed;
    top: 100px;
    right: 20px;
    background: ${type === 'success' ? 'var(--green)' : type === 'error' ? 'var(--red)' : 'var(--blue)'};
    color: white;
    padding: 16px 24px;
    border-radius: 12px;
    font-family: 'DM Sans', sans-serif;
    font-size: 14px;
    font-weight: 500;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    z-index: 10000;
    animation: slideIn 0.3s ease-out;
  `;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-out';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Add animation keyframes
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from {
      transform: translateX(400px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  
  @keyframes slideOut {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(400px);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);

// Save sample user data for demo
if (!localStorage.getItem('sportsai_user')) {
  const sampleUser = {
    name: 'Athlete',
    xp: 8420,
    nextBeltXP: 12000,
    streak: 8,
    belt: 'Blue Belt',
    sessions: 24,
    improvement: 18
  };
  localStorage.setItem('sportsai_user', JSON.stringify(sampleUser));
}
