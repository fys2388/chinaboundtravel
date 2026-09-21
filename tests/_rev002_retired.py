"""REV002 退役不变量 —— 单一事实来源。

背景
----
REV002 是一个 CTA 位实验：在运输指南里插一个 Trip.com 联盟 CTA（affiliate-mid-cta
partner="trip"），测量 affiliate_click_rate。2026-09-21 清理未获批联盟计划时，
Trip.com 的联盟 key 从 hugo.toml 移除，那个 CTA 被换成普通编辑性外链。

但注册表里 status 仍是 RUNNING / decision PENDING——这是一个登记为「运行中」、
实际已无法测量的实验。没有它的 affiliate 仪表，任何 REV002 的转化率数据都是无源之水。

为什么改断言而不是恢复内容
--------------------------
原有 12 个测试断言 `transportation-train-tickets-mid` 恰好出现 1 次、
`affiliate-mid-cta` 出现 2 次、`partner="trip"` 存在——也就是断言那个 CTA
字节未变。断言的对象正是我们**故意删掉**的东西，恢复它等于把刚清理掉的缺陷装回去。

新不变量是**更强**的：撤下必须保持住，同时编辑性推荐必须保留。

用法::

    from _rev002_retired import assert_rev002_retired, assert_rev002_registry_retired

    def test_rev002_cta_unchanged():
        assert_rev002_retired(TRANSPORT)

    def test_rev002_registry_retired():
        assert_rev002_registry_retired((REPO / "reports/revenue/REV002_EXPERIMENT_REGISTRY.csv"))
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Union

#: CTA 被替换成的编辑性外链文本。只要它还在，读者仍能点到 Trip.com。
EDITORIAL_LINK_TEXT = "Compare Train Tickets on Trip.com"
#: 编辑性外链的目标域名。不是短链，不产生佣金——这是诚实的推荐，不是联盟占位。
EDITORIAL_LINK_DOMAIN = "https://www.trip.com/"


def assert_rev002_retired(text: str, *, label: str = "REV002 post") -> None:
    """断言 REV002 的联盟仪表已退役、编辑性推荐仍在。

    断言「撤下保持住」而不是「字节未变」。字节比对只能在一份未提交的工作区里
    成立；断言撤下本身则能在任何 checkout 上验证，并且能抓住两类回归：
      - 有人把 affiliate CTA 悄悄加回去（把未获批计划重新接上）
      - 有人把编辑性推荐也一起删了（Trip.com 推荐本身是成立的）
    """
    assert "affiliate-mid-cta" not in text, (
        f"{label}: affiliate-mid-cta 短码应已撤下（Trip.com 计划未获批）"
    )
    for lit in ('partner="trip"', 'partner = "trip"', "partner=\"trip\""):
        assert lit not in text, f"{label}: {lit!r} 应已撤下"
    assert EDITORIAL_LINK_TEXT in text, (
        f"{label}: 编辑性推荐 {EDITORIAL_LINK_TEXT!r} 应保留——"
        "撤掉联盟仪表不等于撤掉推荐"
    )
    assert EDITORIAL_LINK_DOMAIN in text, (
        f"{label}: 编辑性外链目标 {EDITORIAL_LINK_DOMAIN!r} 应保留"
    )


def assert_rev002_registry_retired(registry_path: Union[str, Path]) -> dict:
    """断言注册表反映现实：实验已退役，不是 RUNNING / PENDING。"""
    p = Path(registry_path)
    with p.open(encoding="utf-8") as f:
        row = next(csv.DictReader(f))
    assert row["experiment_id"] == "REV002"
    assert row["status"] == "RETIRED", (
        f"REV002 status={row['status']!r}——它的 affiliate 仪表已撤下，"
        "没有可测量的实验还在运行中"
    )
    assert row["decision"] == "RETIRED_INVALID_INSTRUMENT", (
        f"REV002 decision={row['decision']!r}——应记录退役原因"
    )
    return row
