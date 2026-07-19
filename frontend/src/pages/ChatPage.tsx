import { useEffect, useRef, useState } from "react";
import { App, Button, Collapse, Empty, Input, Spin, Typography } from "antd";
import { SendOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import { useConversationStore } from "../store/conversationStore";
import ExpertCards from "../components/ExpertCards";
import TokenRing from "../components/TokenRing";
import { colors } from "../theme/theme";
import { fmtTime } from "../utils/time";

export default function ChatPage() {
  const { message } = App.useApp();
  const messages = useConversationStore((s) => s.messages);
  const sending = useConversationStore((s) => s.sending);
  const loadingMessages = useConversationStore((s) => s.loadingMessages);
  const streamingStatus = useConversationStore((s) => s.streamingStatus);
  const statusTrail = useConversationStore((s) => s.statusTrail);
  const contextStat = useConversationStore((s) => s.contextStat);
  const sendMessage = useConversationStore((s) => s.sendMessage);

  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending, streamingStatus]);

  const onSend = async () => {
    const q = input.trim();
    if (!q || sending) return;
    setInput("");
    try {
      await sendMessage(q);
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const empty = messages.length === 0 && !loadingMessages;

  return (
    <div
      className="content-surface"
      style={{
        height: "calc(100vh - 112px)",
        padding: 20,
        display: "flex",
        flexDirection: "column",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* 对话框大背景：淡足球场纹理（中圈/中线/禁区/角球弧），不挡文字 */}
      <svg
        aria-hidden
        viewBox="0 0 400 600"
        preserveAspectRatio="xMidYMid slice"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.16, pointerEvents: "none", zIndex: 0 }}
      >
        <g fill="none" stroke={colors.sage} strokeWidth={3}>
          <line x1="15" y1="300" x2="385" y2="300" />
          <circle cx="200" cy="300" r="58" />
          <circle cx="200" cy="300" r="4" fill={colors.sage} stroke="none" />
          <rect x="120" y="15" width="160" height="80" />
          <rect x="160" y="15" width="80" height="40" />
          <rect x="120" y="505" width="160" height="80" />
          <rect x="160" y="545" width="80" height="40" />
          <path d="M15 30 A15 15 0 0 1 30 15" />
          <path d="M370 15 A15 15 0 0 1 385 30" />
          <path d="M385 570 A15 15 0 0 1 370 585" />
          <path d="M30 585 A15 15 0 0 1 15 570" />
        </g>
      </svg>

      <Typography.Title level={5} style={{ margin: "0 0 12px", position: "relative", zIndex: 1 }}>
        对话预测
      </Typography.Title>

      <div style={{ flex: 1, overflowY: "auto", paddingRight: 4, position: "relative", zIndex: 1 }}>
        {loadingMessages && (
          <div style={{ textAlign: "center", paddingTop: 40 }}>
            <Spin />
          </div>
        )}
        {empty && (
          <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Empty description="输入一场比赛，开始预测" />
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", marginBottom: 14 }}>
              <div
                style={{
                  maxWidth: "78%",
                  background: "rgba(238,241,234,0.78)", // 半透明，透出背景球场
                  padding: "10px 14px",
                  borderRadius: 14,
                  whiteSpace: "pre-wrap",
                }}
              >
                {m.content}
              </div>
              {m.created_at && (
                <div style={{ fontSize: 11, color: colors.textPlaceholder, marginTop: 4 }}>
                  {fmtTime(m.created_at)}
                </div>
              )}
            </div>
          ) : (
            <div
              key={i}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                maxWidth: "86%",
                marginBottom: 14,
              }}
            >
              <ExpertCards experts={m.experts} />
              <div
                className="md-body"
                style={{
                  alignSelf: "stretch",
                  background: "rgba(255,255,255,0.78)", // 半透明，透出背景球场
                  border: `1px solid ${colors.border}`,
                  padding: "10px 16px",
                  borderRadius: 14,
                  minWidth: 48,
                }}
              >
                {m.content ? (
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                ) : (
                  <span style={{ color: colors.textPlaceholder }}>▋</span>
                )}
              </div>
              {m.created_at && (
                <div style={{ fontSize: 11, color: colors.textPlaceholder, marginTop: 4 }}>
                  {fmtTime(m.created_at)}
                </div>
              )}
            </div>
          )
        )}

        {/* 分析过程：实时进度 + 可折叠留痕 */}
        {sending && streamingStatus && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: colors.textSecondary, marginBottom: 10 }}>
            <Spin size="small" /> {streamingStatus}
          </div>
        )}
        {statusTrail.length > 0 && (
          <Collapse
            ghost
            size="small"
            style={{ marginBottom: 12 }}
            items={[
              {
                key: "trail",
                label: (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    分析过程（{statusTrail.length} 步）
                  </Typography.Text>
                ),
                children: (
                  <div style={{ fontSize: 12, color: colors.textSecondary, lineHeight: 1.9 }}>
                    {statusTrail.map((s, i) => (
                      <div key={i}>· {s}</div>
                    ))}
                  </div>
                ),
              },
            ]}
          />
        )}

        <div ref={bottomRef} />
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 12, position: "relative", zIndex: 1 }}>
        <Input.TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          placeholder="输入你想预测的比赛，例如：巴西 vs 德国 谁会赢？（Enter 发送，Shift+Enter 换行）"
          autoSize={{ minRows: 1, maxRows: 4 }}
          disabled={sending}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={onSend}
          loading={sending}
          style={{ height: "auto" }}
        >
          发送
        </Button>
      </div>

      {contextStat && (
        <div style={{ marginTop: 6, display: "flex", justifyContent: "flex-start", position: "relative", zIndex: 1 }}>
          <TokenRing stat={contextStat} />
        </div>
      )}
    </div>
  );
}
