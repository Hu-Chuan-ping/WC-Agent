import { Button, Empty, Input, List, Tag, Typography } from "antd";
import { PlusOutlined, SendOutlined } from "@ant-design/icons";
import { colors } from "../theme/theme";

// 静态壳页：会话列表 + 对话区。后端接口（会话管理、发送消息）将在切片 2 接入。
const MOCK_SESSIONS = [
  { id: "1", title: "阿根廷 vs 法国 会不会重演决赛", time: "刚刚" },
  { id: "2", title: "英格兰小组出线概率", time: "昨天" },
];

export default function ChatPage() {
  return (
    <div style={{ display: "flex", gap: 16, height: "calc(100vh - 112px)" }}>
      {/* 会话列表 */}
      <div className="content-surface" style={{ width: 260, padding: 12, display: "flex", flexDirection: "column" }}>
        <Button type="primary" icon={<PlusOutlined />} block style={{ marginBottom: 12 }}>
          新建对话
        </Button>
        <List
          dataSource={MOCK_SESSIONS}
          renderItem={(item) => (
            <List.Item style={{ padding: "10px 12px", borderRadius: 12, cursor: "pointer" }}>
              <div style={{ width: "100%" }}>
                <div style={{ fontWeight: 500, fontSize: 14, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {item.title}
                </div>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {item.time}
                </Typography.Text>
              </div>
            </List.Item>
          )}
        />
      </div>

      {/* 对话区 */}
      <div className="content-surface" style={{ flex: 1, padding: 20, display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <Typography.Title level={5} style={{ margin: 0 }}>
            对话预测
          </Typography.Title>
          <Tag color="default" style={{ color: colors.textSecondary }}>
            示例 · 待接后端
          </Tag>
        </div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Empty description="选择或新建一个对话，开始预测比赛" />
        </div>
        <Input.Search
          size="large"
          placeholder="输入你想预测的比赛，例如：巴西 vs 德国 谁会赢？"
          enterButton={<Button type="primary" icon={<SendOutlined />}>发送</Button>}
          disabled
        />
      </div>
    </div>
  );
}
