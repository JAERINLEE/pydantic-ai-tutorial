// chart-template.jsx
// Notion DB 통계 차트 시각화 템플릿 (React + Recharts)
// 사용법: DATA 배열을 Notion 데이터로 교체

import { useState } from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";

const COLORS = ["#4F86F7", "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"];

// ✏️ Notion DB 데이터로 교체
const DATA = [
  { name: "1월", 매출: 4000, 지출: 2400, 성장률: 12 },
  { name: "2월", 매출: 3000, 지출: 1398, 성장률: -8 },
  { name: "3월", 매출: 5000, 지출: 2800, 성장률: 25 },
  { name: "4월", 매출: 4500, 지출: 2000, 성장률: 15 },
];

// ✏️ Pie 차트용 데이터
const PIE_DATA = [
  { name: "온라인", value: 45 },
  { name: "오프라인", value: 30 },
  { name: "파트너", value: 25 },
];

const CHART_TYPES = [
  { id: "bar", label: "📊 Bar" },
  { id: "line", label: "📈 Line" },
  { id: "pie", label: "🥧 Pie" },
];

export default function NotionChart() {
  const [activeChart, setActiveChart] = useState("bar");

  return (
    <div style={{ fontFamily: "'Pretendard', 'Apple SD Gothic Neo', sans-serif", padding: "24px", background: "#F7F7F5", minHeight: "100vh" }}>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: "700", color: "#1a1a1a", margin: "0 0 4px 0" }}>
          📊 데이터 대시보드
        </h1>
        <p style={{ color: "#888", fontSize: "14px", margin: 0 }}>Notion DB 연동 통계 차트</p>
      </div>

      {/* 차트 유형 선택 탭 */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "24px" }}>
        {CHART_TYPES.map(ct => (
          <button key={ct.id} onClick={() => setActiveChart(ct.id)} style={{
            padding: "8px 16px", borderRadius: "8px", border: "none", cursor: "pointer",
            background: activeChart === ct.id ? "#1a1a1a" : "white",
            color: activeChart === ct.id ? "white" : "#666",
            fontSize: "14px", fontWeight: activeChart === ct.id ? "600" : "400",
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          }}>
            {ct.label}
          </button>
        ))}
      </div>

      {/* 차트 영역 */}
      <div style={{ background: "white", borderRadius: "12px", padding: "24px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
        <ResponsiveContainer width="100%" height={350}>
          {activeChart === "bar" ? (
            <BarChart data={DATA}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="매출" fill={COLORS[0]} radius={[4,4,0,0]} />
              <Bar dataKey="지출" fill={COLORS[1]} radius={[4,4,0,0]} />
            </BarChart>
          ) : activeChart === "line" ? (
            <LineChart data={DATA}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="성장률" stroke={COLORS[2]} strokeWidth={2} dot={{ r: 5 }} />
            </LineChart>
          ) : (
            <PieChart>
              <Pie data={PIE_DATA} cx="50%" cy="50%" outerRadius={130} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                {PIE_DATA.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* 요약 통계 카드 */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px", marginTop: "16px" }}>
        {[
          { label: "총 매출", value: `${DATA.reduce((s, d) => s + d.매출, 0).toLocaleString()}만원`, color: COLORS[0] },
          { label: "총 지출", value: `${DATA.reduce((s, d) => s + d.지출, 0).toLocaleString()}만원`, color: COLORS[1] },
          { label: "평균 성장률", value: `${(DATA.reduce((s, d) => s + d.성장률, 0) / DATA.length).toFixed(1)}%`, color: COLORS[2] },
        ].map((stat, i) => (
          <div key={i} style={{ background: "white", borderRadius: "10px", padding: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)", borderTop: `3px solid ${stat.color}` }}>
            <div style={{ fontSize: "12px", color: "#888", marginBottom: "4px" }}>{stat.label}</div>
            <div style={{ fontSize: "20px", fontWeight: "700", color: "#1a1a1a" }}>{stat.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
