import { Tooltip } from "antd";
import type { ContextStats } from "../api/conversation";
import { colors } from "../theme/theme";

// 上下文占用圆环：当前会话 token / 模型窗口。hover 显示具体数值 + 模型名。
// 占比越高颜色越暖（绿→金→红），提示上下文在变满。

function ringColor(pct: number): string {
  if (pct >= 0.85) return "#D08C7A"; // 偏红：接近上限
  if (pct >= 0.5) return colors.gold; // 暖金：过半
  return colors.sage; // 鼠尾草绿：宽裕
}

export default function TokenRing({ stat }: { stat: ContextStats | null }) {
  if (!stat || !stat.max_context) return null;
  const pct = Math.min(1, stat.context_tokens / stat.max_context);
  const pctText = (pct * 100).toFixed(pct < 0.1 ? 1 : 0);
  const size = 32;
  const stroke = 4;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const color = ringColor(pct);

  const tip = (
    <div style={{ fontSize: 12, lineHeight: 1.8 }}>
      <div>
        上下文占用：{stat.context_tokens.toLocaleString()} / {stat.max_context.toLocaleString()} tokens
      </div>
      <div>占比：{pctText}%</div>
      <div>模型：{stat.model}</div>
    </div>
  );

  return (
    <Tooltip title={tip} placement="top">
      <div style={{ display: "inline-flex", alignItems: "center", gap: 8, cursor: "default" }}>
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={colors.border} strokeWidth={stroke} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={c * (1 - pct)}
            style={{ transition: "stroke-dashoffset .4s ease, stroke .4s ease" }}
          />
        </svg>
        <span style={{ fontSize: 12, color: colors.textSecondary }}>
          {stat.model} · {pctText}%
        </span>
      </div>
    </Tooltip>
  );
}
