import { apiClient } from "./client";

// 与后端资料接口一一对应（backend/app/api/v1/user.py）。
export interface Profile {
  username: string | null;
  nickname: string | null;
  avatar_url: string | null;
  signature: string | null;
  favorite_teams: string | null;
  favorite_players: string | null;
}

export type ProfileUpdate = Pick<
  Profile,
  "nickname" | "signature" | "favorite_teams" | "favorite_players"
>;

export const profileApi = {
  get: () => apiClient.post<Profile>("/profile/get").then((r) => r.data),
  update: (data: ProfileUpdate) =>
    apiClient.post<Profile>("/profile/update", data).then((r) => r.data),
};
