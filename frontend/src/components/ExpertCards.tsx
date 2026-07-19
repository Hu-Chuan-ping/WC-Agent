import ReactMarkdown from "react-markdown";
import type { ExpertTake } from "../api/conversation";
import { colors } from "../theme/theme";

// 圆桌专家会诊卡片：三张(状态/历史/市场)平铺在最终答案上方，会诊时错峰淡入。
// 每位专家用专属主题色（顶部色条 + 图标 + 标题同色）降低识别成本；三级字体层级。
// 数据两路：直播时来自 store 当轮 experts；翻历史时来自 message.meta.experts。

const ACCENTS: Record<string, { emoji: string; color: string }> = {
  status: { emoji: "⚡", color: "#7EA06E" }, // 状态/战力 —— 绿色（竞技/状态）
  history: { emoji: "📚", color: "#9B84C4" }, // 历史交锋 —— 紫色（历史/档案）
  market: { emoji: "💹", color: "#6A93C0" }, // 市场 —— 蓝色（金融/数据）
};
const FALLBACK = { emoji: "🧠", color: colors.sage };

export default function ExpertCards({ experts }: { experts?: ExpertTake[] }) {
  if (!experts || experts.length === 0) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 12, width: "100%" }}>
      <style>{`@keyframes expertIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}`}</style>
      {experts.map((e, i) => {
        const a = ACCENTS[e.name] ?? FALLBACK;
        return (
          <div
            key={e.name + i}
            style={{
              flex: "1 1 240px",
              minWidth: 220,
              height: 350, // 固定高度：三张齐平，长文本不再撑爆整行
              display: "flex",
              flexDirection: "column",
              background: colors.bgCard,
              border: `1px solid ${colors.border}`,
              borderTop: `3px solid ${a.color}`, // 顶部色条区分维度
              borderRadius: 12,
              padding: 18,
              animation: "expertIn .35s ease both",
              animationDelay: `${i * 90}ms`,
            }}
          >
            {/* 标题：图标 + 名称，同专属色，16px/600（固定不压缩） */}
            <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 10, flexShrink: 0 }}>
              <span style={{ fontSize: 16, lineHeight: 1 }}>{a.emoji}</span>
              <span style={{ fontSize: 16, fontWeight: 600, color: a.color }}>{e.title}</span>
            </div>
            {/* 正文：14px/400，行高 1.6；超出部分本卡内滚动 */}
            <div
              className="md-body"
              style={{
                flex: 1,
                overflowY: "auto",
                fontSize: 14,
                lineHeight: 1.6,
                color: colors.textPrimary,
                paddingRight: 4,
              }}
            >
              <ReactMarkdown>{e.text}</ReactMarkdown>
            </div>
          </div>
        );
      })}
    </div>
  );
}
