import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App as AntdApp, ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import { antdTheme } from "./theme/theme";
import "./styles/global.css";

// 应用入口：全局注入 AntD 主题(设计系统) + 中文文案 + 路由 + 消息上下文。
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ConfigProvider theme={antdTheme} locale={zhCN}>
      <AntdApp>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  </StrictMode>
);
