import { apiClient } from "./client";

// 与后端预测接口一一对应（backend/app/api/v1/prediction.py）。
export interface ScoreProb {
  score: string;
  p: number;
}

export interface PredictionItem {
  match_id: string;
  match: string;
  kickoff_time: string | null;
  predicted_score: string | null; // 概率最高比分
  predicted_probs: string; // "主/平/客"
  score_dist: ScoreProb[]; // 多概率比分分布
  actual_score: string | null; // 如 "0-0（4-3）"
  status: "pending" | "hit" | "half" | "miss";
  session_id: string | null;
}

export interface PredictionSummary {
  total: number;
  resolved: number;
  hit: number;
  half: number;
  miss: number;
  hit_rate: number | null;
  avg_rps_agent: number | null;
  avg_rps_odds: number | null;
  avg_brier_agent: number | null;
  avg_brier_odds: number | null;
  beats_odds: number;
}

export interface Overview {
  total: number;
  resolved: number;
  avg_rps_agent: number | null;
  avg_rps_odds: number | null;
  avg_brier_agent: number | null;
  avg_brier_odds: number | null;
  verdict: string;
}

export const predictionApi = {
  list: () => apiClient.post<PredictionItem[]>("/predictions/list").then((r) => r.data),
  summary: () => apiClient.post<PredictionSummary>("/predictions/summary").then((r) => r.data),
  overview: () => apiClient.post<Overview>("/predictions/overview").then((r) => r.data),
  resolve: () => apiClient.post<{ resolved: number }>("/predictions/resolve").then((r) => r.data),
};
