from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from config import COMPETITION_RULES

DEFAULT_AWARD_LEVEL = "一等奖"


@dataclass(frozen=True)
class SinglePersonRule:
    category: str
    task: str
    education_level: str
    participant_count: int


def build_single_person_rules() -> list[SinglePersonRule]:
    rules: list[SinglePersonRule] = []
    for category, tasks in COMPETITION_RULES.items():
        for task, rule in tasks.items():
            if int(rule.get("participant_count", 0)) != 1:
                continue
            allowed_levels = list(rule.get("allowed_levels") or [])
            if not allowed_levels:
                continue
            rules.append(
                SinglePersonRule(
                    category=category,
                    task=task,
                    education_level=allowed_levels[0],
                    participant_count=1,
                )
            )
    if not rules:
        raise RuntimeError("未找到可用的一人赛项规则")
    return rules


def make_phone(prefix_num: int, index: int, *, base: int) -> str:
    return str(base + prefix_num * 10000 + index).zfill(11)


def build_registration_rows(
    *,
    count: int,
    prefix: str,
    status: str,
    reviewed_by: str,
    award_level: str,
) -> dict:
    if count <= 0:
        raise ValueError("count 必须大于 0")

    rules = build_single_person_rules()
    reviewed_at = datetime.now().isoformat() if status == "approved" else None
    prefix_num = sum(ord(ch) for ch in prefix) % 50000

    registrations: list[dict] = []
    match_no_rows: list[dict] = []
    award_rows: list[dict] = []
    coach_rows: list[dict] = []

    for index in range(count):
        rule = rules[index % len(rules)]
        seq = f"{index:04d}"

        participant_name = f"{prefix}_学生{seq}"
        teacher_name = f"{prefix}_老师{seq}"
        leader_name = f"{prefix}_领队{seq}"
        school_name = f"{prefix}_测试学校{index % 20:02d}"
        participant_phone = make_phone(prefix_num, index, base=13000000000)
        teacher_phone = make_phone(prefix_num, index, base=15000000000)
        leader_phone = make_phone(prefix_num, index, base=17000000000)
        participant_email = f"{prefix.lower()}_{seq}@example.com"
        match_no = f"{prefix}{seq}"

        registration = {
            "openid": f"{prefix}_openid_{seq}",
            "category": rule.category,
            "task": rule.task,
            "education_level": rule.education_level,
            "participant_count": 1,
            "school_name": school_name,
            "school_region": "广东省",
            "school_city": "深圳市",
            "school_district": "南山区",
            "teacher_name": teacher_name,
            "teacher_phone": teacher_phone,
            "leader_name": leader_name,
            "leader_phone": leader_phone,
            "participant_phone": participant_phone,
            "participant_email": participant_email,
            "contact_name": participant_name,
            "contact_phone": participant_phone,
            "contact_email": participant_email,
            "status": status,
            "reviewed_at": reviewed_at,
            "reviewed_by": reviewed_by if reviewed_at else None,
            "match_no": match_no,
            "award_level": award_level,
            "participants": [
                {
                    "seq_no": 1,
                    "participant_name": participant_name,
                }
            ],
        }
        registrations.append(registration)

        match_no_rows.append({"手机号": participant_phone, "参赛号": match_no})
        award_rows.append({"参赛号": match_no, "获奖等级": award_level})
        coach_rows.append({"指导老师姓名": teacher_name, "指导老师电话": teacher_phone})

    return {
        "meta": {
            "prefix": prefix,
            "count": count,
            "status": status,
            "reviewed_by": reviewed_by if reviewed_at else None,
            "created_at": datetime.now().isoformat(),
            "single_person_rules": [asdict(rule) for rule in rules],
        },
        "registrations": registrations,
        "match_no_rows": match_no_rows,
        "award_rows": award_rows,
        "coach_rows": coach_rows,
    }
