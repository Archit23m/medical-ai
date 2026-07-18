const chat = document.getElementById('chat');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');
const emergencyBanner = document.getElementById('emergencyBanner');
const emergencyText = document.getElementById('emergencyText');

let conversation = [];

function addUserBubble(text) {
  const div = document.createElement('div');
  div.className = 'bubble-user';
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function addAgentBubble(html) {
  const div = document.createElement('div');
  div.className = 'bubble-agent';
  div.innerHTML = html;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function renderFollowUps(questions) {
  let html = `<div>A few quick questions to narrow this down:</div><ul class="followups">`;
  questions.forEach(q => html += `<li>${escapeHtml(q)}</li>`);
  html += `</ul>`;
  addAgentBubble(html);
}

function renderResult(result) {
  const urgency = result.urgency || 'MODERATE';
  let html = `
    <div class="gauge-row">
      <span class="gauge-label">URGENCY</span>
      <div class="gauge-track"><div class="gauge-fill ${urgency}"></div></div>
      <span class="gauge-value ${urgency}">${urgency}</span>
    </div>
  `;

  if (result.possible_causes && result.possible_causes.length) {
    html += `<div class="causes">`;
    result.possible_causes.forEach(c => {
      html += `
        <div class="cause">
          <span class="cause-name">${escapeHtml(c.condition)}</span>
          <span class="cause-likelihood">${escapeHtml(c.likelihood)}</span>
          <div class="cause-why">${escapeHtml(c.why)}</div>
        </div>`;
    });
    html += `</div>`;
  }

  html += `
    <div class="recommendation">
      <span class="label">RECOMMENDATION</span>
      ${escapeHtml(result.recommendation || '')}
    </div>
  `;

  addAgentBubble(html);
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

async function send() {
  const text = input.value.trim();
  if (!text) return;

  addUserBubble(text);
  input.value = '';
  sendBtn.disabled = true;
  emergencyBanner.classList.remove('show');

  conversation.push({ role: 'user', content: text });

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation }),
    });
    const data = await res.json();

    if (data.emergency) {
      emergencyText.textContent = 'Detected: ' + data.matched_keywords.join(', ');
      emergencyBanner.classList.add('show');
      emergencyBanner.scrollIntoView({ behavior: 'smooth' });
      conversation = []; // reset — don't continue reasoning on an emergency
      sendBtn.disabled = false;
      return;
    }

    conversation.push({ role: 'assistant', content: JSON.stringify(data) });

    if (data.needs_more_info && data.follow_up_questions && data.follow_up_questions.length) {
      renderFollowUps(data.follow_up_questions);
    } else {
      renderResult(data);
    }
  } catch (err) {
    addAgentBubble('<em>Something went wrong reaching the server. Please try again.</em>');
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

sendBtn.addEventListener('click', send);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    send();
  }
});
