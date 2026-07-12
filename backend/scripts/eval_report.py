"""评估报告：先结算已结束的比赛，再打印全局 你 vs 赔率 的平均 RPS/Brier。

用法（backend 目录、venv 下，需 Docker 的 MySQL 在跑）：
    python scripts/eval_report.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.eval import resolver  # noqa: E402
from app.infra.db.mysql_client import close_pool  # noqa: E402
from app.infra.repositories import match_repository  # noqa: E402


async def main() -> None:
    n = await resolver.resolve_pending()
    print(f"本次结算 {n} 场")
    agg = await match_repository.aggregate()
    print("―― 全局评估报告 ――")
    print(f"权威预测数: {agg.get('total')}  已结算: {agg.get('resolved')}")
    ra, ro = agg.get("avg_rps_agent"), agg.get("avg_rps_odds")
    if ra is not None:
        print(f"平均 RPS  你={ra:.4f}" + (f"  赔率={ro:.4f}" if ro is not None else ""))
        if ro is not None:
            print("结论:", "✅ 打赢了赔率" if ra < ro else "❌ 没打赢赔率")
    print(f"你击败赔率次数: {int(agg.get('agent_beats_odds') or 0)}")
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
