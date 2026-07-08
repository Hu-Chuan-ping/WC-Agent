import { Button, Empty, Input, Tag, Typography } from "antd";
import { SendOutlined } from "@ant-design/icons";
import { colors } from "../theme/theme";

// 对话区。会话列表已移到左侧边栏；这里只负责当前对话的消息流 + 输入。
// 发送消息、加载历史等将在切片 2 接入后端。
export default function ChatPage() {
  return (
    <div
      className="content-surface"
      style={{
        height: "calc(100vh - 112px)",
        padding: 20,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <Typography.Title level={5} style={{ margin: 0 }}>
          对话预测
        </Typography.Title>
        <Tag color="default" style={{ color: colors.textSecondary }}>
          示例 · 待接后端
        </Tag>
      </div>

      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Empty description="在左侧选择或新建一个对话，开始预测比赛" />
      </div>

      <Input.Search
        size="large"
        placeholder="输入你想预测的比赛，例如：巴西 vs 德国 谁会赢？"
        enterButton={
          <Button type="primary" icon={<SendOutlined />}>
            发送
          </Button>
        }
        disabled
      />
    </div>
  );
}
