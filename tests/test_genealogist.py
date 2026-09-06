from chaindesk.agents.genealogist import Genealogist, UnionFind


def test_union_find_merges():
    uf = UnionFind()
    uf.union("a", "b")
    uf.union("b", "c")
    assert uf.find("a") == uf.find("c")
    assert uf.find("d") != uf.find("a")


def test_cluster_requires_min_shared_launches():
    crew = ["0x" + f"{i:040x}" for i in range(1, 4)]
    tourist = "0x" + "9" * 40
    entries = {}
    for t in range(5):
        rows = [(100 + t * 1000 + i, w) for i, w in enumerate(crew)]
        if t == 0:
            rows.append((100, tourist))  # shows up once, must not join
        entries[f"tok{t}"] = rows
    g = Genealogist(window_blocks=30, min_shared=4)
    clusters = g.cluster(entries, kinds={crew[0]: "eoa", crew[1]: "eoa", crew[2]: "7702"})
    assert len(clusters) == 1
    assert set(clusters[0].members) == set(crew)
    assert clusters[0].shared_launches == 5
    assert clusters[0].kinds == {"eoa": 2, "7702": 1}
    assert tourist not in clusters[0].members


def test_window_breaks_link():
    a, b = "0x" + "1" * 40, "0x" + "2" * 40
    entries = {f"tok{t}": [(1000 * t, a), (1000 * t + 500, b)] for t in range(6)}  # 500 blocks apart
    assert Genealogist(window_blocks=30, min_shared=4).cluster(entries) == []
    assert len(Genealogist(window_blocks=600, min_shared=4).cluster(entries)) == 1


def test_bundlers_and_router_excluded():
    a, b, bundler = "0x" + "1" * 40, "0x" + "2" * 40, "0x4337" + "0" * 36
    entries = {f"tok{t}": [(t, a), (t, b), (t, bundler)] for t in range(6)}
    c = Genealogist().cluster(entries)
    assert len(c) == 1 and bundler not in c[0].members


def test_crowd_set_picks_anchor_cluster():
    a, b, c = ("0x" + ch * 40 for ch in "abc")
    entries = {f"tok{t}": [(t, a), (t, b)] for t in range(6)}
    clusters = Genealogist().cluster(entries)
    assert Genealogist.crowd_set(clusters, a) == {a, b}
    assert Genealogist.crowd_set(clusters, c) == {c}


def test_wallet_kind():
    assert Genealogist.wallet_kind("0x") == "eoa"
    assert Genealogist.wallet_kind("0xef0100" + "ab" * 20) == "7702"
    assert Genealogist.wallet_kind("0x6080") == "contract"
