#!/usr/bin/env python3
"""
将本地生成的 registrations.json 导入到数据库。

示例：
  ./venv/bin/python scripts/import_registration_load_test_bundle.py --input tmp/load-test-bundle/LOAD20260408_registrations.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app, db
from models import Application, ApplicationParticipant


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导入报名压测数据包")
    parser.add_argument("--input", required=True, help="本地生成的 registrations.json 路径")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise SystemExit(f"文件不存在: {input_path}")

    registrations = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(registrations, list) or not registrations:
        raise SystemExit("registrations.json 内容无效，必须是非空数组")

    application_ids: list[int] = []
    participant_ids: list[int] = []

    with app.app_context():
        for record in registrations:
            participants = list(record.get("participants") or [])
            application = Application(
                openid=record.get("openid"),
                category=record["category"],
                task=record["task"],
                education_level=record["education_level"],
                participant_count=int(record["participant_count"]),
                school_name=record["school_name"],
                school_region=record.get("school_region", ""),
                school_city=record.get("school_city", ""),
                school_district=record.get("school_district", ""),
                teacher_name=record.get("teacher_name", ""),
                leader_name=record.get("leader_name", ""),
                contact_name=record["contact_name"],
                match_no=None,
                award_level=None,
                rejected_reason=None,
                reviewed_at=datetime.fromisoformat(record["reviewed_at"]) if record.get("reviewed_at") else None,
                reviewed_by=record.get("reviewed_by"),
                status=record.get("status", "approved"),
            )

            application.teacher_phone = str(record.get("teacher_phone", "") or "").strip()
            application.leader_phone = str(record.get("leader_phone", "") or "").strip()
            application.participant_phone = str(record.get("participant_phone", "") or "").strip()
            application.participant_email = str(record.get("participant_email", "") or "").strip()
            application.contact_phone = str(record.get("contact_phone", "") or "").strip()
            application.contact_email = str(record.get("contact_email", "") or "").strip()

            db.session.add(application)
            db.session.flush()
            application_ids.append(application.id)

            for participant in participants:
                participant_row = ApplicationParticipant(
                    application_id=application.id,
                    seq_no=int(participant["seq_no"]),
                    participant_name=participant["participant_name"],
                )
                db.session.add(participant_row)
                db.session.flush()
                participant_ids.append(participant_row.id)

        db.session.commit()

    print(
        json.dumps(
            {
                "success": True,
                "input": str(input_path),
                "application_count": len(application_ids),
                "participant_count": len(participant_ids),
                "application_ids_sample": application_ids[:10],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
