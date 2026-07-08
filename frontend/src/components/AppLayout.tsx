import { Avatar, Button, Dropdown, Layout, Menu, Typography, type MenuProps } from "antd";
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
import { colors } from "../theme/theme";

const { Header, Sider, Content } = Layout;

// 用户信息不放进导航，只通过底部用户点击进入。
const NAV_ITEMS = [
  { key: "/chat", icon: <MessageOutlined />, label: "对话预测" },
  { key: "/predictions", icon: <BarChartOutlined />, label: "已预测比赛" },
];

// 历史对话（静态假数据，切片 2 接入后端会话接口后替换）。
const MOCK_SESSIONS = [
  { id: "1", title: "阿根廷 vs 法国 会不会重演决赛" },
  { id: "2", title: "英格兰小组出线概率" },
  { id: "3", title: "巴西 vs 德国 谁会赢" },
  { id: "4", title: "本届黑马球队分析" },
];

/**
 * 登录后的主框架：
 *  顶部 Logo 栏；
 *  左侧栏 = 功能导航 + 新建对话 + 可滚动历史对话 + 底部用户（点击弹出菜单）；
 *  右侧内容区由子路由通过 <Outlet /> 渲染。
 */
export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  // 命中导航项才高亮；用户信息页不属于导航，故可能为空（不高亮任何项）。
  const selectedKey = NAV_ITEMS.find((i) => location.pathname.startsWith(i.key))?.key;

  const userMenu: MenuProps["items"] = [
    { key: "profile", icon: <UserOutlined />, label: "查看用户信息" },
    { type: "divider" },
    { key: "logout", icon: <LogoutOutlined />, label: "退出登录", danger: true },
  ];

  const onUserMenuClick: MenuProps["onClick"] = ({ key }) => {
    if (key === "profile") {
      navigate("/profile");
    } else if (key === "logout") {
      logout();
      navigate("/login", { replace: true });
    }
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
        <Sider width={260} style={{ borderRight: `1px solid ${colors.border}` }}>
          <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            {/* 功能导航 */}
            <Menu
              mode="inline"
              selectedKeys={selectedKey ? [selectedKey] : []}
              onClick={({ key }) => navigate(key)}
              items={NAV_ITEMS}
              style={{ borderInlineEnd: "none", paddingTop: 8 }}
            />

            {/* 新建对话 */}
            <div style={{ padding: "12px 12px 8px" }}>
              <Button type="primary" icon={<PlusOutlined />} block onClick={() => navigate("/chat")}>
                新建对话
              </Button>
            </div>

            {/* 历史对话（可滚动） */}
            <div style={{ padding: "0 16px 4px" }}>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                历史对话
              </Typography.Text>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: "0 8px 8px" }}>
              {MOCK_SESSIONS.map((s) => (
                <div key={s.id} className="session-item" onClick={() => navigate("/chat")}>
                  <div
                    style={{
                      fontSize: 14,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {s.title}
                  </div>
                </div>
              ))}
            </div>

            {/* 底部：当前用户，点击弹出菜单 */}
            <Dropdown
              menu={{ items: userMenu, onClick: onUserMenuClick }}
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
                  <div
                    style={{
                      fontWeight: 600,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
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
    </Layout>
  );
}
