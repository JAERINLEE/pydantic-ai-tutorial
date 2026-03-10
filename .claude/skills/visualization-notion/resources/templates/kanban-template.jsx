// kanban-template.jsx
// Notion DB 칸반 보드 시각화 템플릿
// 사용법: STATUS_COLUMNS, CARDS 배열을 Notion 데이터로 교체

import { useState } from "react";

const STATUS_COLUMNS = [
  { id: "backlog", label: "백로그", color: "#E8E8E8", textColor: "#666" },
  { id: "inprogress", label: "진행중", color: "#D3E5FF", textColor: "#1E40AF" },
  { id: "review", label: "검토중", color: "#FFF3CC", textColor: "#92400E" },
  { id: "done", label: "완료", color: "#D4EDDA", textColor: "#166534" },
];

const PRIORITY_COLORS = {
  "높음": "#FF4444",
  "중간": "#FF8C00",
  "낮음": "#44BB44",
  "high": "#FF4444",
  "medium": "#FF8C00",
  "low": "#44BB44",
};

// ✏️ 여기에 Notion DB 데이터를 채워넣으세요
const CARDS = [
  {
    id: "1",
    title: "예시 태스크 1",
    status: "inprogress",
    priority: "높음",
    assignee: "김철수",
    dueDate: "2026-03-01",
    points: 3,
  },
  // ... Notion 데이터로 교체
];

function getDday(dateStr) {
  if (!dateStr) return null;
  const diff = Math.ceil((new Date(dateStr) - new Date()) / (1000 * 60 * 60 * 24));
  if (diff < 0) return { label: `D+${Math.abs(diff)}`, color: "#FF4444" };
  if (diff === 0) return { label: "D-day", color: "#FF8C00" };
  return { label: `D-${diff}`, color: diff <= 3 ? "#FF8C00" : "#666" };
}

function KanbanCard({ card }) {
  const dday = getDday(card.dueDate);
  return (
    <div style={{
      background: "white",
      borderRadius: "8px",
      padding: "12px",
      marginBottom: "8px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
      borderLeft: `3px solid ${PRIORITY_COLORS[card.priority] || "#ccc"}`,
    }}>
      <div style={{ fontWeight: "600", fontSize: "14px", marginBottom: "8px", color: "#1a1a1a" }}>
        {card.title}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "4px" }}>
        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
          {card.priority && (
            <span style={{
              fontSize: "11px", padding: "2px 6px", borderRadius: "4px",
              background: PRIORITY_COLORS[card.priority] + "22",
              color: PRIORITY_COLORS[card.priority], fontWeight: "600",
            }}>
              {card.priority}
            </span>
          )}
          {card.points && (
            <span style={{ fontSize: "11px", color: "#666", background: "#f0f0f0", padding: "2px 6px", borderRadius: "4px" }}>
              {card.points}pt
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {card.assignee && (
            <span style={{ fontSize: "12px", color: "#555" }}>👤 {card.assignee}</span>
          )}
          {dday && (
            <span style={{ fontSize: "11px", color: dday.color, fontWeight: "600" }}>{dday.label}</span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function KanbanBoard() {
  const [filter, setFilter] = useState("all");

  const filteredCards = filter === "all" ? CARDS : CARDS.filter(c => c.priority === filter);

  return (
    <div style={{ fontFamily: "'Pretendard', 'Apple SD Gothic Neo', sans-serif", padding: "20px", background: "#F7F7F5", minHeight: "100vh" }}>
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: "700", color: "#1a1a1a", margin: "0 0 4px 0" }}>
          📋 스프린트 칸반 보드
        </h1>
        <p style={{ color: "#888", fontSize: "14px", margin: 0 }}>Notion DB 연동 · 총 {CARDS.length}개 항목</p>
      </div>

      {/* 필터 */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "20px" }}>
        {["all", "높음", "중간", "낮음"].map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: "6px 12px", borderRadius: "6px", border: "none", cursor: "pointer",
            background: filter === f ? "#1a1a1a" : "white",
            color: filter === f ? "white" : "#666",
            fontSize: "13px", fontWeight: filter === f ? "600" : "400",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          }}>
            {f === "all" ? "전체" : f}
          </button>
        ))}
      </div>

      {/* 칸반 컬럼 */}
      <div style={{ display: "flex", gap: "16px", overflowX: "auto", paddingBottom: "16px" }}>
        {STATUS_COLUMNS.map(col => {
          const colCards = filteredCards.filter(c => c.status === col.id);
          return (
            <div key={col.id} style={{ minWidth: "260px", flex: "1" }}>
              <div style={{
                background: col.color, borderRadius: "8px", padding: "10px 12px",
                marginBottom: "12px", display: "flex", justifyContent: "space-between", alignItems: "center",
              }}>
                <span style={{ fontWeight: "700", fontSize: "14px", color: col.textColor }}>{col.label}</span>
                <span style={{
                  background: "rgba(0,0,0,0.1)", color: col.textColor,
                  fontSize: "12px", fontWeight: "700", padding: "2px 8px", borderRadius: "12px",
                }}>{colCards.length}</span>
              </div>
              <div>
                {colCards.map(card => <KanbanCard key={card.id} card={card} />)}
                {colCards.length === 0 && (
                  <div style={{ textAlign: "center", color: "#ccc", fontSize: "13px", padding: "20px" }}>항목 없음</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
