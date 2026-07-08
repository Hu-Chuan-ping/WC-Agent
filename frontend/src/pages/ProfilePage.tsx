import { useEffect, useState } from "react";
import { App, Avatar, Button, Card, Form, Input, Space, Spin, Typography } from "antd";
import { profileApi, type ProfileUpdate } from "../api/profile";
import { useAuthStore } from "../store/authStore";
import { colors } from "../theme/theme";

export default function ProfilePage() {
  const { message } = App.useApp();
  const authUser = useAuthStore((s) => s.user);
  const [form] = Form.useForm<ProfileUpdate>();
  const [username, setUsername] = useState<string | null>(authUser?.username ?? null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    profileApi
      .get()
      .then((p) => {
        setUsername(p.username);
        form.setFieldsValue({
          nickname: p.nickname ?? undefined,
          signature: p.signature ?? undefined,
          favorite_teams: p.favorite_teams ?? undefined,
          favorite_players: p.favorite_players ?? undefined,
        });
      })
      .catch((e) => message.error((e as Error).message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSave = async (values: ProfileUpdate) => {
    setSaving(true);
    try {
      await profileApi.update(values);
      message.success("已保存，并同步为你的专属记忆");
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: "100%", maxWidth: 640 }}>
      <Space align="center">
        <Typography.Title level={4} style={{ margin: 0 }}>
          用户信息
        </Typography.Title>
        <Typography.Text type="secondary">（保存后将作为你的专属记忆，Agent 预测时会参考）</Typography.Text>
      </Space>

      <Card>
        {loading ? (
          <div style={{ textAlign: "center", padding: 40 }}>
            <Spin />
          </div>
        ) : (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
              <Avatar size={64} style={{ backgroundColor: colors.sage, fontSize: 26 }}>
                {(username || "?").slice(0, 1).toUpperCase()}
              </Avatar>
              <div>
                <div style={{ fontSize: 18, fontWeight: 600 }}>{username || "—"}</div>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  头像上传后续接入云端对象存储
                </Typography.Text>
              </div>
            </div>

            <Form form={form} layout="vertical" requiredMark={false} onFinish={onSave}>
              <Form.Item label="昵称" name="nickname">
                <Input placeholder="给自己起个昵称" maxLength={20} />
              </Form.Item>
              <Form.Item label="个性签名" name="signature">
                <Input.TextArea placeholder="一句话介绍自己" rows={2} maxLength={60} />
              </Form.Item>
              <Form.Item label="喜欢的球队" name="favorite_teams">
                <Input placeholder="如：阿根廷、曼城" maxLength={100} />
              </Form.Item>
              <Form.Item label="喜欢的球星" name="favorite_players">
                <Input placeholder="如：梅西、哈兰德" maxLength={100} />
              </Form.Item>
              <Form.Item style={{ marginBottom: 0 }}>
                <Button type="primary" htmlType="submit" loading={saving}>
                  保存
                </Button>
              </Form.Item>
            </Form>
          </>
        )}
      </Card>
    </Space>
  );
}
