import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import DecorBackground from "./components/DecorBackground";
import RequireAuth from "./components/RequireAuth";
import ChatPage from "./pages/ChatPage";
import LoginPage from "./pages/LoginPage";
import PredictionsPage from "./pages/PredictionsPage";
import ProfilePage from "./pages/ProfilePage";

/**
 * 路由表：
 *  /login            公开
 *  /（受保护）        AppLayout 布局下的三个子页
 * 未登录访问受保护页 → RequireAuth 重定向到 /login。
 */
export default function App() {
  return (
    <>
      <DecorBackground />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="predictions" element={<PredictionsPage />} />
          <Route path="profile" element={<ProfilePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
