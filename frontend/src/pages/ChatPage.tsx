import { useEffect, useRef, useState } from "react";
import { App, Button, Collapse, Empty, Input, Spin, Typography } from "antd";
import { SendOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import { useConversationStore } from "../store/conversationStore";
import { colors } from "../theme/theme";

export default function ChatPage() {
  const { message } = App.useApp();
  const messages = useConversationStore((s) => s.messages);
  const sending = useConversationStore((s) => s.sending);
  const loadingMessages = useConversationStore((s) => s.loadingMessages);
  const streamingStatus = useConversationStore((s) => s.streamingStatus);
  const statusTrail = useConversationStore((s) => s.statusTrail);
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
      style={{ height: "calc(100vh - 112px)", padding: 20, display: "flex", flexDirection: "column" }}
    >
      <Typography.Title level={5} style={{ margin: "0 0 12px" }}>
        对话预测
      </Typography.Title>

      <div style={{ flex: 1, overflowY: "auto", paddingRight: 4 }}>
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
            <div key={i} style={{ display: "flex", justifyContent: "flex-end", marginBottom: 14 }}>
              <div
                style={{
                  maxWidth: "78%",
                  background: "#EEF1EA",
                  padding: "10px 14px",
                  borderRadius: 14,
                  whiteSpace: "pre-wrap",
                }}
              >
                {m.content}
              </div>
            </div>
          ) : (
            <div key={i} style={{ display: "flex", justifyContent: "flex-start", marginBottom: 14 }}>
              <div
                className="md-body"
                style={{
                  maxWidth: "82%",
                  background: "#FFFFFF",
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

      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
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
    </div>
  );
}
