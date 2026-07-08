import { Button, Card, Space, Table, Tag, Typography } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { colors } from "../theme/theme";

// 静态壳页：已预测比赛列表 + 命中状态 + 汇总。后端接口将在切片 3 接入。
interface PredictionRow {
  key: string;
  match: string;
  kickoff: string;
  predicted: string;
  actual: string;
  status: "pending" | "hit" | "half" | "miss";
}

const STATUS_META: Record<PredictionRow["status"], { text: string; color: string }> = {
  pending: { text: "待验证", color: "default" },
  hit: { text: "全中", color: "green" },
  half: { text: "半中", color: "gold" },
  miss: { text: "未中", color: "red" },
};

const MOCK_ROWS: PredictionRow[] = [
  { key: "1", match: "葡萄牙 vs 西班牙", kickoff: "2026-06-18 03:00", predicted: "1 - 2", actual: "1 - 2", status: "hit" },
  { key: "2", match: "英格兰 vs 巴拿马", kickoff: "2026-06-20 21:00", predicted: "3 - 0", actual: "2 - 0", status: "half" },
  { key: "3", match: "巴西 vs 德国", kickoff: "2026-06-25 03:00", predicted: "2 - 1", actual: "待开赛", status: "pending" },
];

const columns: ColumnsType<PredictionRow> = [
  { title: "比赛信息", dataIndex: "match", key: "match" },
  { title: "比赛时间（北京）", dataIndex: "kickoff", key: "kickoff" },
  {
    title: "预测比分",
    dataIndex: "predicted",
    key: "predicted",
    render: (v) => <span style={{ color: colors.gold, fontWeight: 600 }}>{v}</span>,
  },
  { title: "真实结果", dataIndex: "actual", key: "actual" },
  {
    title: "命中状态",
    dataIndex: "status",
    key: "status",
    render: (s: PredictionRow["status"]) => (
      <Tag color={STATUS_META[s].color}>{STATUS_META[s].text}</Tag>
    ),
  },
];

export default function PredictionsPage() {
  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Space align="center">
          <Typography.Title level={4} style={{ margin: 0 }}>
            已预测比赛
          </Typography.Title>
          <Tag color="default" style={{ color: colors.textSecondary }}>
            示例 · 待接后端
          </Tag>
        </Space>
        <Button icon={<ReloadOutlined />}>刷新赛果</Button>
      </div>

      <Card>
        <Table<PredictionRow> columns={columns} dataSource={MOCK_ROWS} pagination={false} />
      </Card>

      <Card title="预测汇总">
        <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
          <Stat label="总预测" value="12" />
          <Stat label="已结算" value="8" color={colors.sage} />
          <Stat label="全中率" value="37.5%" color={colors.gold} />
          <Stat label="击败赔率" value="3 场" color={colors.sage} />
        </div>
        <Typography.Text type="secondary" style={{ display: "block", marginTop: 16 }}>
          图表区域（准确率趋势 / Brier 对比）将在接入后端后渲染。
        </Typography.Text>
      </Card>
    </Space>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div style={{ fontSize: 28, fontWeight: 700, color: color || colors.textPrimary }}>
        {value}
      </div>
      <div style={{ color: colors.textSecondary, fontSize: 13 }}>{label}</div>
    </div>
  );
}
