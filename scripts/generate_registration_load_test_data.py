#!/usr/bin/env python3
"""
本地生成报名压测数据包，不直接写数据库。

输出：
1. registrations.json：线上导入脚本读取的完整报名数据
2. manifest.json：数据包元信息
3. 参赛号 / 获奖 / 优秀辅导员三份 Excel

示例：
  ./venv/bin/python scripts/generate_registration_load_test_data.py --count 1000 --prefix LOAD20260408
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.registration_load_test_bundle import DEFAULT_AWARD_LEVEL, build_registration_rows


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    default_prefix = f"LOAD{now}"
    parser = argparse.ArgumentParser(description="生成报名压测数据")
    parser.add_argument("--count", type=int, default=1000, help="生成报名条数，默认 1000")
    parser.add_argument("--prefix", type=str, default=default_prefix, help="测试数据前缀，建议保持唯一")
    parser.add_argument(
        "--status",
        choices=["pending", "approved"],
        default="approved",
        help="报名状态，默认 approved，更贴近后续导入场景",
    )
    parser.add_argument(
        "--reviewed-by",
        type=str,
        default="load-test-script",
        help="当 status=approved 时写入的 reviewed_by",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default="tmp/load-test-bundle/manifest.json",
        help="输出 manifest 路径",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="tmp/load-test-bundle",
        help="数据包输出目录",
    )
    parser.add_argument(
        "--award-level",
        type=str,
        default=DEFAULT_AWARD_LEVEL,
        help="导出获奖 Excel 时使用的默认获奖等级",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bundle = build_registration_rows(
        count=args.count,
        prefix=args.prefix,
        status=args.status,
        reviewed_by=args.reviewed_by,
        award_level=args.award_level,
    )

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest).resolve()
    ensure_parent_dir(manifest_path)
    registrations_path = output_dir / f"{args.prefix}_registrations.json"
    match_no_path = output_dir / f"{args.prefix}_match_no.xlsx"
    awards_path = output_dir / f"{args.prefix}_awards.xlsx"
    coaches_path = output_dir / f"{args.prefix}_excellent_coaches.xlsx"

    registrations_path.write_text(
        json.dumps(bundle["registrations"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    pd.DataFrame(bundle["match_no_rows"]).to_excel(match_no_path, index=False)
    pd.DataFrame(bundle["award_rows"]).to_excel(awards_path, index=False)
    pd.DataFrame(bundle["coach_rows"]).to_excel(coaches_path, index=False)

    manifest = {
        **bundle["meta"],
        "registrations_json": str(registrations_path),
        "match_no_excel": str(match_no_path),
        "awards_excel": str(awards_path),
        "excellent_coaches_excel": str(coaches_path),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "success": True,
        "prefix": args.prefix,
        "count": args.count,
        "status": args.status,
        "manifest": str(manifest_path),
        "registrations_json": str(registrations_path),
        "match_no_excel": str(match_no_path),
        "awards_excel": str(awards_path),
        "excellent_coaches_excel": str(coaches_path),
        "next_steps": [
            "1. 将 registrations.json 复制到线上",
            "2. 在线上执行 import_registration_load_test_bundle.py 导入报名数据",
            "3. 管理员导入参赛号 / 获奖 / 优秀辅导员 Excel",
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
