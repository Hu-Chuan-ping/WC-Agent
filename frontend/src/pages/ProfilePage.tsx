import { Avatar, Button, Card, Form, Input, Space, Typography } from "antd";
import { UserOutlined } from "@ant-design/icons";
import { useAuthStore } from "../store/authStore";
import { colors } from "../theme/theme";

// 静态壳页：用户资料（昵称/签名/喜欢的球队球星）。这些将作为长期记忆存后端，切片 4 接入。
export default function ProfilePage() {
  const user = useAuthStore((s) => s.user);

  return (
    <Space direction="vertical" size={16} style={{ width: "100%", maxWidth: 640 }}>
      <Space align="center">
        <Typography.Title level={4} style={{ margin: 0 }}>
          用户信息
        </Typography.Title>
        <Typography.Text type="secondary">（保存后将作为你的专属记忆）</Typography.Text>
      </Space>

      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
          <Avatar size={64} style={{ backgroundColor: colors.sage }} icon={<UserOutlined />} />
          <div>
            <div style={{ fontSize: 18, fontWeight: 600 }}>{user?.username || "—"}</div>
            <Button size="small" style={{ marginTop: 8 }}>
              更换头像
            </Button>
          </div>
        </div>

        <Form layout="vertical" requiredMark={false}>
          <Form.Item label="昵称">
            <Input placeholder="给自己起个昵称" maxLength={20} />
          </Form.Item>
          <Form.Item label="个性签名">
            <Input.TextArea placeholder="一句话介绍自己" rows={2} maxLength={60} />
          </Form.Item>
          <Form.Item label="喜欢的球队">
            <Input placeholder="如：阿根廷、曼城" />
          </Form.Item>
          <Form.Item label="喜欢的球星">
            <Input placeholder="如：梅西、哈兰德" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" disabled>
              保存（待接后端）
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </Space>
  );
}
