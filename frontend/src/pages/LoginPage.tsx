import { useCallback, useEffect, useState } from "react";
import {
  App,
  Button,
  Card,
  Form,
  Input,
  Segmented,
  Space,
  Typography,
} from "antd";
import { LockOutlined, SafetyCertificateOutlined, UserOutlined } from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";
import { authApi, type Captcha } from "../api/auth";
import { useAuthStore } from "../store/authStore";
import { colors } from "../theme/theme";

type Mode = "login" | "register";

interface FormValues {
  username: string;
  password: string;
  captcha_text: string;
}

/**
 * 登录 / 注册页。同一张卡片用 Segmented 切换两种模式，共用一张验证码。
 * 提交流程：整理参数 → 调后端 → 成功则写登录态并跳主页；失败提示并刷新验证码。
 */
export default function LoginPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [mode, setMode] = useState<Mode>("login");
  const [captcha, setCaptcha] = useState<Captcha | null>(null);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm<FormValues>();

  const refreshCaptcha = useCallback(async () => {
    try {
      setCaptcha(await authApi.getCaptcha());
    } catch {
      message.error("验证码加载失败，请刷新页面");
    }
  }, [message]);

  // 首次进入加载验证码
  useEffect(() => {
    refreshCaptcha();
  }, [refreshCaptcha]);

  const onFinish = async (values: FormValues) => {
    if (!captcha) return;
    setLoading(true);
    try {
      const payload = { ...values, captcha_id: captcha.captcha_id };
      const res =
        mode === "login"
          ? await authApi.login(payload)
          : await authApi.register(payload);

      setAuth(res.access_token, {
        user_id: res.user_id,
        username: res.username,
      });
      message.success(mode === "login" ? "登录成功" : "注册成功，已自动登录");

      const from = (location.state as { from?: Location })?.from?.pathname;
      navigate(from || "/chat", { replace: true });
    } catch (e) {
      message.error((e as Error).message);
      // 验证码是一次性的，失败后换一张
      form.setFieldValue("captcha_text", "");
      refreshCaptcha();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        position: "relative",
        zIndex: 1,
      }}
    >
      <Card
        style={{ width: 420, boxShadow: `0 8px 32px ${colors.shadow}` }}
        styles={{ body: { padding: "32px 36px" } }}
      >
        <Space
          direction="vertical"
          size={4}
          style={{ width: "100%", textAlign: "center", marginBottom: 20 }}
        >
          <div style={{ fontSize: 40, lineHeight: 1 }}>⚽</div>
          <Typography.Title level={3} style={{ margin: 0 }}>
            WC Agent
          </Typography.Title>
          <Typography.Text type="secondary">
            2026 世界杯比分预测 · 你的专属足球分析助手
          </Typography.Text>
        </Space>

        <Segmented<Mode>
          block
          value={mode}
          onChange={(v) => {
            setMode(v);
            form.resetFields();
            refreshCaptcha();
          }}
          options={[
            { label: "登录", value: "login" },
            { label: "注册", value: "register" },
          ]}
          style={{ marginBottom: 24 }}
        />

        <Form form={form} layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item
            name="username"
            rules={[
              { required: true, message: "请输入用户名" },
              mode === "register"
                ? { min: 3, max: 32, message: "用户名 3–32 个字符" }
                : {},
            ]}
          >
            <Input
              size="large"
              prefix={<UserOutlined style={{ color: colors.textPlaceholder }} />}
              placeholder="用户名"
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: "请输入密码" },
              mode === "register"
                ? { min: 6, max: 64, message: "密码 6–64 个字符" }
                : {},
            ]}
          >
            <Input.Password
              size="large"
              prefix={<LockOutlined style={{ color: colors.textPlaceholder }} />}
              placeholder="密码"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </Form.Item>

          <Form.Item
            name="captcha_text"
            rules={[{ required: true, message: "请输入验证码" }]}
          >
            <Space.Compact style={{ width: "100%" }}>
              <Input
                size="large"
                prefix={
                  <SafetyCertificateOutlined
                    style={{ color: colors.textPlaceholder }}
                  />
                }
                placeholder="验证码"
                maxLength={4}
              />
              <div
                onClick={refreshCaptcha}
                title="点击刷新"
                style={{
                  width: 120,
                  height: 42,
                  borderRadius: 10,
                  border: `1px solid ${colors.border}`,
                  overflow: "hidden",
                  cursor: "pointer",
                  flexShrink: 0,
                  background: colors.bgLayout,
                }}
              >
                {captcha && (
                  <img
                    src={captcha.image}
                    alt="验证码"
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  />
                )}
              </div>
            </Space.Compact>
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, marginTop: 8 }}>
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              block
              loading={loading}
            >
              {mode === "login" ? "登 录" : "注 册"}
            </Button>
          </Form.Item>
        </Form>

        {/* 仅开发模式：跳过登录直接预览内页（不连后端）。打包上线自动消失。 */}
        {import.meta.env.DEV && (
          <Button
            type="link"
            block
            style={{ marginTop: 12, color: colors.textSecondary }}
            onClick={() => {
              setAuth("preview-token", {
                user_id: "preview",
                username: "预览用户",
              });
              navigate("/chat", { replace: true });
            }}
          >
            跳过登录 · 预览界面（仅开发）
          </Button>
        )}
      </Card>
    </div>
  );
}
