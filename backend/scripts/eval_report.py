"""评估报告：先结算已结束的比赛，再打印 你 vs 赔率 的平均 Brier。

用法（backend 目录、venv 下，需 Docker 的 MySQL 在跑）：
    python scripts/eval_report.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.eval import repo, resolver  # noqa: E402
from app.db.mysql_client import close_pool  # noqa: E402


async def main() -> None:
    await repo.ensure_tables()
    n = await resolver.resolve_pending()
    print(f"本次结算 {n} 场")
    agg = await repo.aggregate()
    print("―― 评估报告 ――")
    print(f"总预测数: {agg.get('total')}  已结算: {agg.get('resolved')}")
    ba, bo = agg.get("avg_brier_agent"), agg.get("avg_brier_odds")
    if ba is not None:
        print(f"平均 Brier  你={ba:.4f}" + (f"  赔率={bo:.4f}" if bo is not None else ""))
        if bo is not None:
            print("结论:", "✅ 你打赢了赔率" if ba < bo else "❌ 没打赢赔率（≈复述市场）")
    print(f"你击败赔率次数: {int(agg.get('agent_beats_odds') or 0)}")
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
