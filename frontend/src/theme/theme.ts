import type { ThemeConfig } from "antd";

/**
 * 设计系统：所有颜色/圆角集中在这里，组件里不硬编码色值。
 * 改主题只改这一处。
 */
export const colors = {
  bgBase: "#F8F7F4", // 奶油白：主背景
  bgLayout: "#F0F2F5", // 浅雾灰：页面辅助背景
  bgCard: "#FFFFFF", // 卡片背景
  textPrimary: "#1F2933", // 主文字
  textSecondary: "#6B7280", // 次级文字
  textPlaceholder: "#9CA3AF", // 占位文字
  sage: "#A8B59F", // 强调色 A：鼠尾草绿（主按钮/成功/正向）
  sageHover: "#97a68c",
  gold: "#C8A97E", // 强调色 B：暖金（比分/置信度/数据高亮）
  border: "#E5E7EB",
  shadow: "rgba(0, 0, 0, 0.04)",
} as const;

/** 圆角规范（造型语言：一律柔和圆角，禁止直角）。 */
export const radii = {
  card: 16,
  button: 12,
  input: 10,
  tag: 8,
} as const;

/** 传给 AntD 全局 ConfigProvider 的主题配置。 */
export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: colors.sage,
    colorSuccess: colors.sage,
    colorInfo: colors.sage,
    colorText: colors.textPrimary,
    colorTextSecondary: colors.textSecondary,
    colorTextPlaceholder: colors.textPlaceholder,
    colorBorder: colors.border,
    colorBgContainer: colors.bgCard,
    colorBgLayout: colors.bgLayout,
    borderRadius: radii.button,
    fontFamily:
      '-apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", Roboto, sans-serif',
    boxShadowSecondary: `0 4px 16px ${colors.shadow}`,
  },
  components: {
    Card: { borderRadiusLG: radii.card },
    Input: { borderRadius: radii.input, controlHeight: 42 },
    Button: { borderRadius: radii.button, controlHeight: 42 },
    Tag: { borderRadiusSM: radii.tag },
    Layout: {
      bodyBg: colors.bgBase,
      siderBg: colors.bgCard,
      headerBg: colors.bgCard,
    },
    Menu: { itemBorderRadius: radii.button, itemSelectedBg: "#EEF1EA" },
  },
};
