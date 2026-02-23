const mockCourses = [
  { code: "CPSC 323", name: "Intro to Systems Programming", prof: "Eisenstat", rating: 4.2, diff: "Hard", time: "Mon/Wed 2:30pm" }, 
  { code: "PSYC 110", name: "Introduction to Psychology", prof: "Laurie Santos", rating: 4.9, diff: "Easy", time: "MWF 10:30am" },
  { code: "ECON 121", name: "Intermediate Microeconomics", prof: "Costas Meghir", rating: 4.5, diff: "Medium", time: "Tue/Thu 1pm" },
  { code: "MUSI 110", name: "Listening to Music", prof: "Craig Wright", rating: 4.8, diff: "Easy", time: "MWF 11:35am" },
  { code: "PHIL 126", name: "Philosophy of Mind", prof: "Zoltán Szabó", rating: 4.3, diff: "Medium", time: "Mon/Wed 11:35am" },
  { code: "S&DS 230", name: "Data Analysis & Statistics", prof: "John Lafferty", rating: 4.1, diff: "Medium", time: "Tue/Thu 9am" },
  { code: "HIST 116", name: "The American Revolution", prof: "Joanne Freeman", rating: 4.7, diff: "Easy", time: "Tue/Thu 11:35am" },
  { code: "ENGL 114", name: "Writing the Essay", prof: "Various", rating: 4.0, diff: "Easy", time: "Various" },
];

function suggest(query) {
  const q = query.toLowerCase();
  return mockCourses.filter(c =>
    c.name.toLowerCase().includes(q) ||
    c.code.toLowerCase().includes(q) ||
    c.prof.toLowerCase().includes(q) ||
    (q.includes("easy") && c.diff === "Easy") ||
    (q.includes("hard") && c.diff === "Hard") ||
    (q.includes("popular") && c.rating >= 4.7) ||
    (q.includes("small") && ["PHIL 126", "HIST 116"].includes(c.code)) ||
    (q.includes("cs") && c.code.startsWith("CPSC")) ||
    (q.includes("music") && c.code.startsWith("MUSI")) ||
    (q.includes("humanity") || q.includes("hu")) && ["MUSI 110","PHIL 126","HIST 116","ENGL 114"].includes(c.code) ||
    (q.includes("distrib") && c.diff === "Easy") ||
    (q.includes("intro") && c.name.toLowerCase().includes("intro")) ||
    (q.includes("seminar") && ["PHIL 126", "HIST 116"].includes(c.code)) ||
    (q.includes("data") || q.includes("stats")) && c.code.startsWith("S&DS") ||
    (q.includes("writing") || q.includes("english")) && c.code.startsWith("ENGL")
  ).slice(0, 3);
}

function getReply(query, courses) {
  if (courses.length === 0) return "I couldn't find a match for that. Try searching by subject, difficulty (easy/hard), or type like 'seminar' or 'intro class'!";
  const intro = [
    `Here are ${courses.length} courses you might love 👇`,
    `Found some great options for you!`,
    `These look like a great fit based on what you said:`,
  ];
  return intro[Math.floor(Math.random() * intro.length)];
}

// DOM helpers
const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("input");

function scrollBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addMessage(role, text, courses = []) {
  const msg = document.createElement("div");
  msg.className = `msg ${role}`;

  if (role === "ai") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "Y";
    msg.appendChild(avatar);
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  // Add course cards inside bubble
  if (courses.length > 0) {
    courses.forEach(c => {
      const card = document.createElement("div");
      card.className = "course-card";
      card.innerHTML = `
        <div class="course-code">${c.code}</div>
        <div class="course-name">${c.name}</div>
        <div class="course-meta">
          <span>${c.prof}</span>
          <span>·</span>
          <span>${c.time}</span>
          <span>·</span>
          <span class="course-rating">★ ${c.rating}</span>
          <span>·</span>
          <span>${c.diff}</span>
        </div>
      `;
      bubble.appendChild(card);
    });
  }

  msg.appendChild(bubble);
  messagesEl.appendChild(msg);
  scrollBottom();
}

function showTyping() {
  const el = document.createElement("div");
  el.className = "msg ai typing-msg";
  el.innerHTML = `
    <div class="avatar">Y</div>
    <div class="dots">
      <div class="dot"></div>
      <div class="dot"></div>
      <div class="dot"></div>
    </div>
  `;
  messagesEl.appendChild(el);
  scrollBottom();
  return el;
}

function sendMessage(text) {
  const q = text || inputEl.value.trim();
  if (!q) return;
  inputEl.value = "";
  inputEl.style.height = "auto";

  addMessage("user", q);

  const typingEl = showTyping();

  setTimeout(() => {
    typingEl.remove();
    const courses = suggest(q);
    const reply = getReply(q, courses);
    addMessage("ai", reply, courses);
  }, 800);
}

function sendChip(text) {
  sendMessage(text);
}

function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 80) + "px";
}

// Initial greeting
window.onload = () => {
  setTimeout(() => {
    addMessage("ai", "Hey! I'm your Yale course guide 👋 Tell me what you're looking for — a subject, vibe, difficulty, or time slot — and I'll find the best classes for you.");
  }, 200);
};