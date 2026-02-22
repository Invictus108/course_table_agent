import { useState, useEffect, useRef } from "react";

const mockCourses = [
  {
    id: 1, code: "CPSC 323", name: "Introduction to Systems Programming",
    professor: "Stanley Eisenstat", credits: 4, term: "Spring 2025",
    schedule: "Mon/Wed 2:30–3:45pm", area: "QR", distributional: "Sc",
    rating: 4.2, difficulty: 3.8, enrollment: 120,
    description: "Systems programming in C. Memory management, processes, concurrency, and networking fundamentals.",
    tags: ["CS", "Systems", "C", "Low-level"],
  },
  {
    id: 2, code: "ECON 121", name: "Intermediate Microeconomics",
    professor: "Costas Meghir", credits: 4, term: "Spring 2025",
    schedule: "Tue/Thu 1:00–2:15pm", area: "QR", distributional: "So",
    rating: 4.5, difficulty: 3.5, enrollment: 80,
    description: "Consumer and producer theory, market equilibrium, welfare economics, and game theory.",
    tags: ["Economics", "Theory", "Math"],
  },
  {
    id: 3, code: "PSYC 110", name: "Introduction to Psychology",
    professor: "Laurie Santos", credits: 3, term: "Spring 2025",
    schedule: "Mon/Wed/Fri 10:30–11:20am", area: "So", distributional: "Sc",
    rating: 4.9, difficulty: 2.1, enrollment: 350,
    description: "Survey of major areas of psychological science: perception, cognition, emotion, personality, behavior, and social influences.",
    tags: ["Psychology", "Survey", "Popular"],
  },
  {
    id: 4, code: "S&DS 230", name: "Data Analysis and Statistics",
    professor: "John Lafferty", credits: 4, term: "Spring 2025",
    schedule: "Tue/Thu 9:00–10:15am", area: "QR", distributional: "Sc",
    rating: 4.1, difficulty: 3.2, enrollment: 95,
    description: "Statistical methods for data analysis including regression, classification, and data visualization using R.",
    tags: ["Stats", "Data Science", "R", "QR"],
  },
  {
    id: 5, code: "PHIL 126", name: "Philosophy of Mind",
    professor: "Zoltán Szabó", credits: 3, term: "Spring 2025",
    schedule: "Mon/Wed 11:35am–12:50pm", area: "Hu", distributional: "HU",
    rating: 4.3, difficulty: 3.0, enrollment: 60,
    description: "Consciousness, intentionality, personal identity, and the relationship between mind and body.",
    tags: ["Philosophy", "AI", "Consciousness", "HU"],
  },
  {
    id: 6, code: "MUSI 110", name: "Listening to Music",
    professor: "Craig Wright", credits: 3, term: "Spring 2025",
    schedule: "Mon/Wed/Fri 11:35am–12:25pm", area: "Hu", distributional: "HU",
    rating: 4.8, difficulty: 1.8, enrollment: 400,
    description: "How to listen to and understand Western classical music from the Middle Ages to the present.",
    tags: ["Music", "Arts", "Easy", "HU"],
  },
];

const suggestCourses = (query) => {
  if (!query.trim()) return [];
  const q = query.toLowerCase();
  return mockCourses
    .filter(c =>
      c.name.toLowerCase().includes(q) ||
      c.tags.some(t => t.toLowerCase().includes(q)) ||
      c.description.toLowerCase().includes(q) ||
      c.code.toLowerCase().includes(q) ||
      (q.includes("easy") && c.difficulty < 2.5) ||
      (q.includes("hard") && c.difficulty > 3.5) ||
      (q.includes("cs") && c.tags.includes("CS")) ||
      (q.includes("math") && (c.area === "QR" || c.tags.includes("Math"))) ||
      (q.includes("humanity") || q.includes("hu") && c.area === "Hu") ||
      (q.includes("popular") && c.enrollment > 200) ||
      (q.includes("small") && c.enrollment < 70)
    )
    .sort((a, b) => b.rating - a.rating);
};

const StarRating = ({ value }) => {
  return (
    <span style={{ color: "#f5c842", fontSize: "12px", letterSpacing: "1px" }}>
      {"★".repeat(Math.round(value))}{"☆".repeat(5 - Math.round(value))}
      <span style={{ color: "#94a3b8", marginLeft: 6, fontSize: 11 }}>{value.toFixed(1)}</span>
    </span>
  );
};

const DifficultyBar = ({ value }) => {
  const pct = (value / 5) * 100;
  const color = value < 2 ? "#4ade80" : value < 3.5 ? "#facc15" : "#f87171";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 5, borderRadius: 99, background: "#1e293b", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 99, transition: "width 0.6s ease" }} />
      </div>
      <span style={{ fontSize: 11, color: "#94a3b8", minWidth: 24 }}>{value.toFixed(1)}</span>
    </div>
  );
};

const CourseCard = ({ course, onAdd, added, style }) => {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? "#0f172a" : "#0a0f1e",
        border: `1px solid ${hovered ? "#3b82f6" : "#1e293b"}`,
        borderRadius: 16,
        padding: "22px 24px",
        cursor: "default",
        transition: "all 0.25s ease",
        transform: hovered ? "translateY(-3px)" : "none",
        boxShadow: hovered ? "0 12px 40px rgba(59,130,246,0.15)" : "none",
        display: "flex",
        flexDirection: "column",
        gap: 12,
        ...style,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: 11, color: "#3b82f6", fontFamily: "'Space Mono', monospace", letterSpacing: 2, marginBottom: 4 }}>
            {course.code}
          </div>
          <div style={{ fontSize: 17, fontWeight: 700, color: "#f1f5f9", lineHeight: 1.3 }}>
            {course.name}
          </div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 3 }}>{course.professor}</div>
        </div>
        <button
          onClick={() => onAdd(course)}
          style={{
            background: added ? "#166534" : "#1e3a5f",
            border: `1px solid ${added ? "#22c55e" : "#3b82f6"}`,
            borderRadius: 99,
            color: added ? "#4ade80" : "#93c5fd",
            fontSize: 11,
            padding: "5px 14px",
            cursor: "pointer",
            whiteSpace: "nowrap",
            fontWeight: 600,
            transition: "all 0.2s",
            flexShrink: 0,
            marginLeft: 12,
          }}
        >
          {added ? "✓ Added" : "+ Add"}
        </button>
      </div>

      <p style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.6, margin: 0 }}>
        {course.description}
      </p>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {course.tags.map(t => (
          <span key={t} style={{
            background: "#0f2040", border: "1px solid #1e3a5f",
            color: "#60a5fa", fontSize: 10, padding: "2px 10px",
            borderRadius: 99, fontFamily: "'Space Mono', monospace",
          }}>{t}</span>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 20px", paddingTop: 8, borderTop: "1px solid #1e293b" }}>
        <div>
          <div style={{ fontSize: 10, color: "#475569", marginBottom: 3, textTransform: "uppercase", letterSpacing: 1 }}>Rating</div>
          <StarRating value={course.rating} />
        </div>
        <div>
          <div style={{ fontSize: 10, color: "#475569", marginBottom: 4, textTransform: "uppercase", letterSpacing: 1 }}>Difficulty</div>
          <DifficultyBar value={course.difficulty} />
        </div>
        <div>
          <div style={{ fontSize: 10, color: "#475569", marginBottom: 3, textTransform: "uppercase", letterSpacing: 1 }}>Schedule</div>
          <div style={{ fontSize: 12, color: "#cbd5e1" }}>{course.schedule}</div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: "#475569", marginBottom: 3, textTransform: "uppercase", letterSpacing: 1 }}>Credits / Area</div>
          <div style={{ fontSize: 12, color: "#cbd5e1" }}>{course.credits} cr · {course.area}</div>
        </div>
      </div>
    </div>
  );
};

const chatSuggestions = [
  "easy humanities for QR credit",
  "small CS systems class",
  "popular intro courses",
  "something with data and stats",
  "philosophy of mind or AI",
];

export default function App() {
  const [messages, setMessages] = useState([
    { role: "ai", text: "Hey! I'm your Yale course guide. Tell me what you're looking for — subject, vibe, difficulty, schedule, distributional requirements — anything works." }
  ]);
  const [input, setInput] = useState("");
  const [results, setResults] = useState([]);
  const [schedule, setSchedule] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("search");
  const chatBottom = useRef(null);

  useEffect(() => {
    chatBottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = (text) => {
    const q = text || input;
    if (!q.trim()) return;
    setInput("");
    setMessages(m => [...m, { role: "user", text: q }]);
    setLoading(true);
    setTimeout(() => {
      const found = suggestCourses(q);
      setResults(found);
      setLoading(false);
      const reply = found.length > 0
        ? `I found ${found.length} course${found.length > 1 ? "s" : ""} that match what you're looking for. Check them out on the right — you can add any to your schedule!`
        : "Hmm, I didn't find a strong match. Try different keywords like a subject, distributional area (QR, HU, So), difficulty level, or time of day.";
      setMessages(m => [...m, { role: "ai", text: reply }]);
    }, 900);
  };

  const addToSchedule = (course) => {
    setSchedule(s => s.find(c => c.id === course.id) ? s.filter(c => c.id !== course.id) : [...s, course]);
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #060b18; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 99px; }
        textarea:focus, input:focus { outline: none; }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }
        .card-appear { animation: fadeUp 0.4s ease both; }
      `}</style>

      <div style={{ minHeight: "100vh", background: "#060b18", fontFamily: "'Syne', sans-serif", color: "#f1f5f9", display: "flex", flexDirection: "column" }}>

        {/* Header */}
        <header style={{ padding: "18px 32px", borderBottom: "1px solid #0f172a", display: "flex", alignItems: "center", justifyContent: "space-between", background: "#060b18", position: "sticky", top: 0, zIndex: 100, backdropFilter: "blur(20px)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: "linear-gradient(135deg, #1d4ed8, #3b82f6)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, fontWeight: 800, color: "white",
              boxShadow: "0 0 20px rgba(59,130,246,0.4)",
            }}>Y</div>
            <div>
              <div style={{ fontSize: 17, fontWeight: 800, letterSpacing: -0.5 }}>CourseAI</div>
              <div style={{ fontSize: 10, color: "#475569", fontFamily: "'Space Mono', monospace", letterSpacing: 1 }}>YALE COURSE SUGGESTER</div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {["search", "schedule"].map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)} style={{
                background: activeTab === tab ? "#1e3a5f" : "transparent",
                border: `1px solid ${activeTab === tab ? "#3b82f6" : "#1e293b"}`,
                color: activeTab === tab ? "#60a5fa" : "#475569",
                borderRadius: 99, padding: "6px 18px", cursor: "pointer",
                fontSize: 12, fontWeight: 700, textTransform: "capitalize",
                transition: "all 0.2s",
              }}>
                {tab === "schedule" ? `My Schedule (${schedule.length})` : "Search"}
              </button>
            ))}
          </div>
        </header>

        <div style={{ flex: 1, display: activeTab === "search" ? "grid" : "block", gridTemplateColumns: "380px 1fr", gap: 0, overflow: "hidden", height: "calc(100vh - 73px)" }}>

          {activeTab === "search" && (
            <>
              {/* Left: Chat */}
              <div style={{ display: "flex", flexDirection: "column", borderRight: "1px solid #0f172a", height: "100%", overflow: "hidden" }}>
                {/* Messages */}
                <div style={{ flex: 1, overflowY: "auto", padding: "24px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
                  {messages.map((m, i) => (
                    <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
                      {m.role === "ai" && (
                        <div style={{ width: 28, height: 28, borderRadius: 8, background: "linear-gradient(135deg,#1d4ed8,#3b82f6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 800, marginRight: 10, flexShrink: 0, marginTop: 2 }}>Y</div>
                      )}
                      <div style={{
                        maxWidth: "78%",
                        background: m.role === "user" ? "#1e3a5f" : "#0f172a",
                        border: `1px solid ${m.role === "user" ? "#3b82f6" : "#1e293b"}`,
                        borderRadius: m.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                        padding: "12px 16px", fontSize: 14, color: "#cbd5e1", lineHeight: 1.6,
                      }}>
                        {m.text}
                      </div>
                    </div>
                  ))}
                  {loading && (
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{ width: 28, height: 28, borderRadius: 8, background: "linear-gradient(135deg,#1d4ed8,#3b82f6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 800 }}>Y</div>
                      <div style={{ display: "flex", gap: 5 }}>
                        {[0, 1, 2].map(i => (
                          <div key={i} style={{ width: 7, height: 7, borderRadius: "50%", background: "#3b82f6", animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite` }} />
                        ))}
                      </div>
                    </div>
                  )}
                  <div ref={chatBottom} />
                </div>

                {/* Suggestions */}
                <div style={{ padding: "0 20px 10px", display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {chatSuggestions.map(s => (
                    <button key={s} onClick={() => handleSend(s)} style={{
                      background: "transparent", border: "1px solid #1e293b",
                      color: "#475569", borderRadius: 99, padding: "4px 12px",
                      fontSize: 11, cursor: "pointer", transition: "all 0.2s",
                      fontFamily: "'Space Mono', monospace",
                    }}
                      onMouseEnter={e => { e.target.style.borderColor = "#3b82f6"; e.target.style.color = "#60a5fa"; }}
                      onMouseLeave={e => { e.target.style.borderColor = "#1e293b"; e.target.style.color = "#475569"; }}
                    >{s}</button>
                  ))}
                </div>

                {/* Input */}
                <div style={{ padding: "12px 20px 20px", borderTop: "1px solid #0f172a" }}>
                  <div style={{ display: "flex", gap: 10, background: "#0f172a", border: "1px solid #1e293b", borderRadius: 14, padding: "10px 14px", alignItems: "flex-end" }}>
                    <textarea
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                      placeholder="Describe what you're looking for..."
                      rows={2}
                      style={{
                        flex: 1, background: "transparent", border: "none",
                        color: "#f1f5f9", fontSize: 14, resize: "none",
                        fontFamily: "'Syne', sans-serif", lineHeight: 1.5,
                      }}
                    />
                    <button onClick={() => handleSend()} style={{
                      background: "linear-gradient(135deg, #1d4ed8, #3b82f6)",
                      border: "none", borderRadius: 10, width: 36, height: 36,
                      cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                      flexShrink: 0, fontSize: 16, color: "white",
                      boxShadow: "0 0 16px rgba(59,130,246,0.4)",
                    }}>↑</button>
                  </div>
                </div>
              </div>

              {/* Right: Results */}
              <div style={{ overflowY: "auto", padding: 28 }}>
                {results.length === 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16, opacity: 0.4 }}>
                    <div style={{ fontSize: 64 }}>📚</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: "#475569" }}>Ask me anything about courses</div>
                    <div style={{ fontSize: 13, color: "#334155", textAlign: "center", maxWidth: 300, lineHeight: 1.6 }}>
                      Try "easy QR credit", "intro CS", "something on Tuesday afternoons", or any subject you're curious about.
                    </div>
                  </div>
                ) : (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 16 }}>
                    {results.map((c, i) => (
                      <div key={c.id} className="card-appear" style={{ animationDelay: `${i * 80}ms` }}>
                        <CourseCard
                          course={c}
                          onAdd={addToSchedule}
                          added={!!schedule.find(s => s.id === c.id)}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          {activeTab === "schedule" && (
            <div style={{ padding: 32, overflowY: "auto", height: "100%" }}>
              <div style={{ marginBottom: 28 }}>
                <h2 style={{ fontSize: 26, fontWeight: 800, marginBottom: 6 }}>My Schedule</h2>
                <p style={{ color: "#475569", fontSize: 14 }}>
                  {schedule.length === 0 ? "No courses added yet. Go to Search and add some!" : `${schedule.length} course${schedule.length > 1 ? "s" : ""} · ${schedule.reduce((a, c) => a + c.credits, 0)} total credits`}
                </p>
              </div>

              {schedule.length > 0 && (
                <>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 16, marginBottom: 32 }}>
                    {schedule.map((c, i) => (
                      <div key={c.id} className="card-appear" style={{ animationDelay: `${i * 80}ms` }}>
                        <CourseCard
                          course={c}
                          onAdd={addToSchedule}
                          added={true}
                        />
                      </div>
                    ))}
                  </div>

                  {/* Summary bar */}
                  <div style={{ background: "#0a0f1e", border: "1px solid #1e293b", borderRadius: 16, padding: "20px 24px", display: "flex", gap: 32, flexWrap: "wrap" }}>
                    <div>
                      <div style={{ fontSize: 10, color: "#475569", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Total Credits</div>
                      <div style={{ fontSize: 28, fontWeight: 800, color: "#3b82f6" }}>{schedule.reduce((a, c) => a + c.credits, 0)}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: "#475569", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Avg Rating</div>
                      <div style={{ fontSize: 28, fontWeight: 800, color: "#f5c842" }}>
                        {(schedule.reduce((a, c) => a + c.rating, 0) / schedule.length).toFixed(1)}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: "#475569", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Avg Difficulty</div>
                      <div style={{ fontSize: 28, fontWeight: 800, color: "#f87171" }}>
                        {(schedule.reduce((a, c) => a + c.difficulty, 0) / schedule.length).toFixed(1)}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, color: "#475569", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Areas Covered</div>
                      <div style={{ display: "flex", gap: 6 }}>
                        {[...new Set(schedule.map(c => c.area))].map(a => (
                          <span key={a} style={{ background: "#1e3a5f", border: "1px solid #3b82f6", color: "#60a5fa", fontSize: 11, padding: "3px 12px", borderRadius: 99 }}>{a}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
