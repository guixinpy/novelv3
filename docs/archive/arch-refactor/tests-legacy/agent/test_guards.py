"""五级风险检测器测试。"""
from __future__ import annotations

from app.agent.guards import GuardSystem


def _rec(name: str, args: dict | None, text: str = "ok", is_error: bool = False):
    return (name, args, is_error, text)


class TestL1GenericRepeat:
    def test_no_trip_below_3(self):
        g = GuardSystem()
        g.record_tool_call(*_rec("read", {"i": 1}))
        g.record_tool_call(*_rec("read", {"i": 1}))
        r = g.check()
        assert not r.tripped

    def test_trips_at_3_identical(self):
        g = GuardSystem()
        for _ in range(3):
            g.record_tool_call(*_rec("read", {"i": 1}))
        r = g.check()
        assert r.tripped
        assert r.level == "L1"

    def test_different_args_no_trip(self):
        g = GuardSystem()
        g.record_tool_call(*_rec("read", {"i": 1}))
        g.record_tool_call(*_rec("read", {"i": 2}))
        g.record_tool_call(*_rec("read", {"i": 3}))
        r = g.check()
        assert not r.tripped


class TestL2PingPong:
    def test_trips_at_2_pairs(self):
        g = GuardSystem()
        for _ in range(2):
            g.record_tool_call(*_rec("write", {}))
            g.record_tool_call(*_rec("read", {}))
        r = g.check()
        assert r.tripped
        assert r.level == "L2"

    def test_no_trip_with_random_sequence(self):
        g = GuardSystem()
        for t in ["a", "b", "c", "d"]:
            g.record_tool_call(*_rec(t, {}))
        r = g.check()
        assert not r.tripped


class TestL3Poll:
    def test_trips_at_4_similar(self):
        g = GuardSystem()
        # L1 won't match because args differ
        for i in range(4):
            g.record_tool_call(*_rec("poll", {"q": f"query{i}"}, "same result text here"))
        r = g.check()
        assert r.tripped
        assert r.level == "L3"

    def test_different_results_no_trip(self):
        g = GuardSystem()
        g.record_tool_call(*_rec("poll", {"q": "q1"}, "{x:1}"))
        g.record_tool_call(*_rec("poll", {"q": "q2"}, "{y:2}"))
        g.record_tool_call(*_rec("poll", {"q": "q3"}, "{z:3}"))
        g.record_tool_call(*_rec("poll", {"q": "q4"}, "[99,100,200]"))
        r = g.check()
        assert not r.tripped


class TestL4UnknownRepeat:
    def test_trips_at_2_unknown(self):
        g = GuardSystem()
        g.record_tool_call(*_rec("nonexistent", {}, '工具 "nonexistent" 不存在', is_error=True))
        g.record_tool_call(*_rec("bogus_tool", {}, '工具 "bogus_tool" 不存在', is_error=True))
        r = g.check()
        assert r.tripped
        assert r.level == "L4"


class TestL5Fuse:
    def test_trips_at_2x_max(self):
        g = GuardSystem()
        for i in range(60):
            g.record_tool_call(*_rec(f"t{i}", {}, str(i)))
        r = g.check(max_iterations=30)
        assert r.tripped
        assert r.level == "L5"

    def test_no_trip_below_2x(self):
        g = GuardSystem()
        for i in range(40):
            g.record_tool_call(*_rec(f"t{i}", {}, str(i)))
        r = g.check(max_iterations=30)
        assert not r.tripped
