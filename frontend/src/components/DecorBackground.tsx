import { colors } from "../theme/theme";

/**
 * 页面底层装饰：右下角一个扁平卡通踢球小人 + 足球，低透明度、轻微模糊，
 * 固定定位、不拦截鼠标、不遮挡内容。营造轻微足球氛围又不喧宾夺主。
 */
export default function DecorBackground() {
  return (
    <div
      aria-hidden
      style={{
        position: "fixed",
        right: -20,
        bottom: -10,
        width: 360,
        height: 360,
        opacity: 0.1, // 8%~12% 区间
        filter: "blur(0.6px)",
        pointerEvents: "none",
        zIndex: 0,
        userSelect: "none",
      }}
    >
      <svg viewBox="0 0 240 240" width="100%" height="100%" fill="none">
        {/* 身体 */}
        <rect x="118" y="70" width="34" height="70" rx="17" fill={colors.sage} />
        {/* 头 */}
        <circle cx="135" cy="52" r="20" fill={colors.sage} />
        {/* 支撑腿 */}
        <rect x="122" y="132" width="18" height="60" rx="9" fill={colors.sage} />
        {/* 抬起的踢球腿（斜向） */}
        <rect
          x="140"
          y="128"
          width="18"
          height="58"
          rx="9"
          fill={colors.sage}
          transform="rotate(38 149 157)"
        />
        {/* 手臂 */}
        <rect
          x="100"
          y="86"
          width="16"
          height="46"
          rx="8"
          fill={colors.sage}
          transform="rotate(28 108 109)"
        />
        {/* 足球 */}
        <circle cx="196" cy="182" r="26" fill={colors.gold} />
        <circle cx="196" cy="182" r="26" stroke={colors.sage} strokeWidth="2" />
        <path
          d="M196 168 l11 8 -4 13 h-14 l-4 -13 z"
          fill={colors.sage}
          opacity="0.7"
        />
      </svg>
    </div>
  );
}
