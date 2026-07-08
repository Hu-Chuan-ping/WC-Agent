import { useEffect, useState } from "react";
import {
  App,
  Avatar,
  Button,
  Dropdown,
  Input,
  Layout,
  Menu,
  Modal,
  Typography,
  type MenuProps,
} from "antd";
import {
  BarChartOutlined,
  LogoutOutlined,
  MessageOutlined,
  MoreOutlined,
  PlusOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { useConversationStore } from "../store/conversationStore";
import type { SessionItem } from "../api/conversation";
import { colors } from "../theme/theme";

const { Header, Sider, Content } = Layout;

// 用户信息不放进导航，只通过底部用户点击进入。
const NAV_ITEMS = [
  { key: "/chat", icon: <MessageOutlined />, label: "对话预测" },
  { key: "/predictions", icon: <BarChartOutlined />, label: "已预测比赛" },
];

const SESSION_ITEMS: MenuProps["items"] = [
  { key: "rename", label: "重命名" },
  { key: "delete", label: "删除", danger: true },
];

export default function AppLayout() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const sessions = useConversationStore((s) => s.sessions);
  const activeId = useConversationStore((s) => s.activeId);
  const loadSessions = useConversationStore((s) => s.loadSessions);
  const newConversation = useConversationStore((s) => s.newConversation);
  const selectSession = useConversationStore((s) => s.selectSession);
  const renameSession = useConversationStore((s) => s.renameSession);
  const deleteSession = useConversationStore((s) => s.deleteSession);
  const resetConversations = useConversationStore((s) => s.reset);

  const [renameTarget, setRenameTarget] = useState<SessionItem | null>(null);
  const [renameText, setRenameText] = useState("");

  useEffect(() => {
    loadSessions().catch(() => void 0);
  }, [loadSessions]);

  const selectedKey = NAV_ITEMS.find((i) => location.pathname.startsWith(i.key))?.key;

  const onLogout = () => {
    logout();
    resetConversations();
    navigate("/login", { replace: true });
  };

  const onNewChat = () => {
    newConversation();
    navigate("/chat");
  };

  const onSelect = (id: string) => {
    selectSession(id).catch((e) => message.error((e as Error).message));
    navigate("/chat");
  };

  const onSessionMenu = (s: SessionItem, key: string) => {
    if (key === "rename") {
      setRenameTarget(s);
      setRenameText(s.title);
    } else if (key === "delete") {
      Modal.confirm({
        title: "删除对话",
        content: `确定删除「${s.title}」？该对话的消息也会一并清除。`,
        okText: "删除",
        okButtonProps: { danger: true },
        cancelText: "取消",
        onOk: () =>
          deleteSession(s.session_id).catch((e) => message.error((e as Error).message)),
      });
    }
  };

  const userMenu: MenuProps["items"] = [
    { key: "profile", icon: <UserOutlined />, label: "查看用户信息" },
    { type: "divider" },
    { key: "logout", icon: <LogoutOutlined />, label: "退出登录", danger: true },
  ];

  return (
    <Layout style={{ minHeight: "100vh", background: "transparent", zIndex: 1, position: "relative" }}>
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          borderBottom: `1px solid ${colors.border}`,
          paddingInline: 24,
        }}
      >
        <span style={{ fontSize: 24 }}>⚽</span>
        <Typography.Title level={4} style={{ margin: 0 }}>
          WC Agent
        </Typography.Title>
      </Header>

      <Layout style={{ background: "transparent" }}>
        <Sider width={260} style={{ borderRight: `1px solid ${colors.border}` }}>
          <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            <Menu
              mode="inline"
              selectedKeys={selectedKey ? [selectedKey] : []}
              onClick={({ key }) => navigate(key)}
              items={NAV_ITEMS}
              style={{ borderInlineEnd: "none", paddingTop: 8 }}
            />

            <div style={{ padding: "12px 12px 8px" }}>
              <Button type="primary" icon={<PlusOutlined />} block onClick={onNewChat}>
                新建对话
              </Button>
            </div>

            <div style={{ padding: "0 16px 4px" }}>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                历史对话
              </Typography.Text>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: "0 8px 8px" }}>
              {sessions.map((s) => (
                <div
                  key={s.session_id}
                  className={`session-item${activeId === s.session_id ? " active" : ""}`}
                  onClick={() => onSelect(s.session_id)}
                  style={{ display: "flex", alignItems: "center", gap: 6 }}
                >
                  <div style={{ flex: 1, fontSize: 14, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {s.title}
                  </div>
                  <Dropdown
                    trigger={["click"]}
                    menu={{ items: SESSION_ITEMS, onClick: ({ key, domEvent }) => { domEvent.stopPropagation(); onSessionMenu(s, key); } }}
                  >
                    <MoreOutlined
                      onClick={(e) => e.stopPropagation()}
                      style={{ color: colors.textSecondary, padding: 4 }}
                    />
                  </Dropdown>
                </div>
              ))}
              {sessions.length === 0 && (
                <Typography.Text type="secondary" style={{ fontSize: 12, paddingLeft: 8 }}>
                  还没有对话，点上方新建
                </Typography.Text>
              )}
            </div>

            <Dropdown
              menu={{
                items: userMenu,
                onClick: ({ key }) => (key === "profile" ? navigate("/profile") : onLogout()),
              }}
              trigger={["click"]}
              placement="topRight"
            >
              <div
                style={{
                  borderTop: `1px solid ${colors.border}`,
                  padding: "12px 16px",
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  cursor: "pointer",
                }}
              >
                <Avatar style={{ backgroundColor: colors.sage, flexShrink: 0 }} icon={<UserOutlined />} />
                <div style={{ flex: 1, overflow: "hidden" }}>
                  <div style={{ fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {user?.username || "未登录"}
                  </div>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    点击查看 / 退出
                  </Typography.Text>
                </div>
                <MoreOutlined style={{ color: colors.textSecondary }} />
              </div>
            </Dropdown>
          </div>
        </Sider>

        <Content style={{ padding: 24, overflow: "auto" }}>
          <Outlet />
        </Content>
      </Layout>

      <Modal
        open={renameTarget !== null}
        title="重命名对话"
        onCancel={() => setRenameTarget(null)}
        onOk={async () => {
          if (renameTarget) {
            await renameSession(renameTarget.session_id, renameText.trim() || renameTarget.title);
          }
          setRenameTarget(null);
        }}
        okText="保存"
        cancelText="取消"
      >
        <Input value={renameText} onChange={(e) => setRenameText(e.target.value)} maxLength={40} />
      </Modal>
    </Layout>
  );
}
