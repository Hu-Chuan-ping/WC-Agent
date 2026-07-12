import { useEffect, useState } from "react";
import { App, Button, Card, Space, Table, Tag, Typography } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  predictionApi,
  type Overview,
  type PredictionItem,
  type PredictionSummary,
} from "../api/prediction";
import { colors } from "../theme/theme";

const STATUS_META: Record<PredictionItem["status"], { text: string; color: string }> = {
  pending: { text: "待验证", color: "default" },
  hit: { text: "全中", color: "green" },
  half: { text: "半中", color: "gold" },
  miss: { text: "未中", color: "red" },
};

function fmtKickoff(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  // 转北京时间展示
  return d.toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const columns: ColumnsType<PredictionItem> = [
  { title: "比赛信息", dataIndex: "match", key: "match" },
  { title: "比赛时间（北京）", dataIndex: "kickoff_time", key: "kickoff_time", render: fmtKickoff },
  {
    title: "最可能比分",
    dataIndex: "predicted_score",
    key: "predicted_score",
    render: (v) => <span style={{ color: colors.gold, fontWeight: 600 }}>{v || "—"}</span>,
  },
  { title: "真实结果", dataIndex: "actual_score", key: "actual_score", render: (v) => v || "待开赛" },
  {
    title: "命中状态",
    dataIndex: "status",
    key: "status",
    render: (s: PredictionItem["status"]) => <Tag color={STATUS_META[s].color}>{STATUS_META[s].text}</Tag>,
  },
];

export default function PredictionsPage() {
  const { message } = App.useApp();
  const [rows, setRows] = useState<PredictionItem[]>([]);
  const [summary, setSummary] = useState<PredictionSummary | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [r, s, o] = await Promise.all([
        predictionApi.list(),
        predictionApi.summary(),
        predictionApi.overview(),
      ]);
      setRows(r);
      setSummary(s);
      setOverview(o);
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      const { resolved } = await predictionApi.resolve();
      message.success(resolved > 0 ? `新结算 ${resolved} 场` : "暂无新结束的比赛");
      await load();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          已预测比赛
        </Typography.Title>
        <Button icon={<ReloadOutlined />} loading={refreshing} onClick={onRefresh}>
          刷新赛果
        </Button>
      </div>

      {summary && (
        <Card title="我的预测汇总">
          <div style={{ display: "flex", gap: 40, flexWrap: "wrap", marginBottom: 20 }}>
            <Stat label="总预测" value={String(summary.total)} />
            <Stat label="已结算" value={String(summary.resolved)} color={colors.sage} />
            <Stat
              label="全中率"
              value={summary.hit_rate === null ? "—" : `${Math.round(summary.hit_rate * 100)}%`}
              color={colors.gold}
            />
            <Stat label="击败赔率" value={`${summary.beats_odds} 场`} color={colors.sage} />
            <Stat
              label="平均 RPS（你/赔率）越低越准"
              value={`${fmt(summary.avg_rps_agent)} / ${fmt(summary.avg_rps_odds)}`}
            />
            <Stat
              label="平均 Brier（你/赔率）"
              value={`${fmt(summary.avg_brier_agent)} / ${fmt(summary.avg_brier_odds)}`}
            />
          </div>
          <DistributionBar hit={summary.hit} half={summary.half} miss={summary.miss} />
        </Card>
      )}

      <Card loading={loading} title="预测明细（点开看多概率比分）">
        <Table<PredictionItem>
          rowKey="match_id"
          columns={columns}
          dataSource={rows}
          pagination={{ pageSize: 10 }}
          expandable={{
            expandedRowRender: (r) => (
              <div style={{ paddingLeft: 8 }}>
                <div style={{ marginBottom: 6, color: colors.textSecondary }}>
                  胜/平/负概率：<b>{r.predicted_probs}</b>
                </div>
                <div style={{ color: colors.textSecondary, marginBottom: 4 }}>比分分布：</div>
                {r.score_dist.length === 0 ? (
                  <Typography.Text type="secondary">—</Typography.Text>
                ) : (
                  <Space size={12} wrap>
                    {r.score_dist.map((d) => (
                      <span key={d.score} style={{ fontSize: 13 }}>
                        <b style={{ color: colors.gold }}>{d.score}</b>：{Math.round(d.p * 100)}%
                      </span>
                    ))}
                  </Space>
                )}
              </div>
            ),
          }}
        />
      </Card>

      {overview && (
        <Card title="全局总预测偏差（所有比赛）">
          <Space size={40} wrap>
            <Stat label="全局已结算" value={`${overview.resolved} / ${overview.total}`} />
            <Stat label="平均 RPS · 你" value={fmt(overview.avg_rps_agent)} color={colors.sage} />
            <Stat label="平均 RPS · 赔率" value={fmt(overview.avg_rps_odds)} color={colors.gold} />
          </Space>
          <Typography.Paragraph style={{ marginTop: 16, marginBottom: 0 }}>
            {overview.verdict}
          </Typography.Paragraph>
        </Card>
      )}
    </Space>
  );
}

function fmt(v: number | null): string {
  return v === null ? "—" : v.toFixed(3);
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div style={{ fontSize: 24, fontWeight: 700, color: color || colors.textPrimary }}>{value}</div>
      <div style={{ color: colors.textSecondary, fontSize: 13 }}>{label}</div>
    </div>
  );
}

function DistributionBar({ hit, half, miss }: { hit: number; half: number; miss: number }) {
  const total = hit + half + miss;
  if (total === 0) return <Typography.Text type="secondary">暂无已结算的预测</Typography.Text>;
  const seg = (n: number, bg: string) =>
    n > 0 ? <div key={bg} style={{ width: `${(n / total) * 100}%`, background: bg }} /> : null;
  return (
    <div>
      <div style={{ display: "flex", height: 16, borderRadius: 8, overflow: "hidden", marginBottom: 8 }}>
        {seg(hit, "#7FA87F")}
        {seg(half, colors.gold)}
        {seg(miss, "#D98A8A")}
      </div>
      <Space size={16}>
        <Legend color="#7FA87F" text={`全中 ${hit}`} />
        <Legend color={colors.gold} text={`半中 ${half}`} />
        <Legend color="#D98A8A" text={`未中 ${miss}`} />
      </Space>
    </div>
  );
}

function Legend({ color, text }: { color: string; text: string }) {
  return (
    <span style={{ fontSize: 13, color: colors.textSecondary }}>
      <span style={{ display: "inline-block", width: 10, height: 10, background: color, borderRadius: 3, marginRight: 6 }} />
      {text}
    </span>
  );
}
