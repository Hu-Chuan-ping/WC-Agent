import ReactMarkdown from "react-markdown";
import type { ExpertTake } from "../api/conversation";
import { colors } from "../theme/theme";

// 圆桌专家会诊卡片：三张(状态/历史/市场)平铺在最终答案上方，会诊时错峰淡入。
// 数据两路：直播时来自 store 当轮 experts；翻历史时来自 message.meta.experts。

const ACCENTS: Record<string, { emoji: string; color: string }> = {
  status: { emoji: "⚡", color: colors.sage }, // 状态/战力 —— 鼠尾草绿
  history: { emoji: "📚", color: colors.gold }, // 历史交锋 —— 暖金
  market: { emoji: "💹", color: "#8CA6B5" }, // 市场 —— 柔蓝
};
const FALLBACK = { emoji: "🧠", color: colors.sage };

export default function ExpertCards({ experts }: { experts?: ExpertTake[] }) {
  if (!experts || experts.length === 0) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 10, width: "100%" }}>
      <style>{`@keyframes expertIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}`}</style>
      {experts.map((e, i) => {
        const a = ACCENTS[e.name] ?? FALLBACK;
        return (
          <div
            key={e.name + i}
            style={{
              flex: "1 1 220px",
              minWidth: 200,
              background: colors.bgCard,
              border: `1px solid ${colors.border}`,
              borderLeft: `3px solid ${a.color}`,
              borderRadius: 12,
              padding: "8px 12px",
              fontSize: 12.5,
              lineHeight: 1.6,
              color: colors.textSecondary,
              animation: "expertIn .35s ease both",
              animationDelay: `${i * 90}ms`,
            }}
          >
            <div style={{ fontWeight: 600, color: colors.textPrimary, marginBottom: 4 }}>
              {a.emoji} {e.title}
            </div>
            <div className="md-body md-compact">
              <ReactMarkdown>{e.text}</ReactMarkdown>
            </div>
          </div>
        );
      })}
    </div>
  );
}
