import { Avatar, Button, Layout, Menu, Typography } from "antd";
import {
  BarChartOutlined,
  LogoutOutlined,
  MessageOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { colors } from "../theme/theme";

const { Header, Sider, Content } = Layout;

const NAV_ITEMS = [
  { key: "/chat", icon: <MessageOutlined />, label: "对话预测" },
  { key: "/predictions", icon: <BarChartOutlined />, label: "已预测比赛" },
  { key: "/profile", icon: <UserOutlined />, label: "用户信息" },
];

/**
 * 登录后的主框架：顶部 Logo 栏 + 左侧导航侧边栏（底部为当前用户 + 退出），
 * 右侧内容区由子路由通过 <Outlet /> 渲染。
 */
export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const selectedKey =
    NAV_ITEMS.find((i) => location.pathname.startsWith(i.key))?.key || "/chat";

  const onLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

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
        <Sider
          width={240}
          style={{
            borderRight: `1px solid ${colors.border}`,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            onClick={({ key }) => navigate(key)}
            items={NAV_ITEMS}
            style={{ borderInlineEnd: "none", paddingTop: 12, flex: 1 }}
          />

          {/* 底部：当前登录用户 + 退出 */}
          <div style={{ borderTop: `1px solid ${colors.border}`, padding: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              <Avatar style={{ backgroundColor: colors.sage }} icon={<UserOutlined />} />
              <div style={{ overflow: "hidden" }}>
                <div style={{ fontWeight: 600, whiteSpace: "nowrap", textOverflow: "ellipsis", overflow: "hidden" }}>
                  {user?.username || "未登录"}
                </div>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  已登录
                </Typography.Text>
              </div>
            </div>
            <Button block icon={<LogoutOutlined />} onClick={onLogout}>
              退出登录
            </Button>
          </div>
        </Sider>

        <Content style={{ padding: 24, overflow: "auto" }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
