from dataclasses import dataclass

LOG = []   # semua event, urut eksekusi global
HB = []    # sisi happens-before: (eid_awal, eid_akhir)


@dataclass
class Message:
    name: str
    sender: int
    receiver: int
    ts: int
    send_eid: int


@dataclass
class Event:
    eid: int
    pid: int
    kind: str
    label: str
    ts: int
    calc: str


class Process:
    def __init__(self, pid):
        self.pid = pid
        self.clock = 0
        self.last_eid = None

    def _log(self, kind, label, calc):
        e = Event(len(LOG), self.pid, kind, label, self.clock, calc)
        LOG.append(e)
        if self.last_eid is not None:          # urutan lokal dalam satu proses
            HB.append((self.last_eid, e.eid))
        self.last_eid = e.eid
        return e

    def internal(self, label):
        old = self.clock
        self.clock += 1                         # Rule 1
        self._log("INTERNAL", label, f"{old}+1")

    def send(self, name, to):
        old = self.clock
        self.clock += 1                         # Rule 2: increment lalu kirim
        e = self._log("SEND", name, f"{old}+1")
        return Message(name, self.pid, to, self.clock, e.eid)

    def receive(self, msg):
        old = self.clock
        self.clock = max(old, msg.ts) + 1       # Rule 3
        e = self._log("RECEIVE", msg.name, f"max({old},{msg.ts})+1")
        HB.append((msg.send_eid, e.eid))        # send -> receive


def simulate():
    P = {i: Process(i) for i in (1, 2, 3)}
    P[1].internal("a")
    P[2].internal("c")
    P[3].internal("d")
    m1 = P[1].send("m1", 2); P[2].receive(m1)
    m2 = P[2].send("m2", 3); P[3].receive(m2)
    m3 = P[3].send("m3", 1); P[1].receive(m3)
    m4 = P[1].send("m4", 2); P[2].receive(m4)
    m5 = P[3].send("m5", 2); P[2].receive(m5)


def name(e):
    return f"P{e.pid}.{e.kind[:4].lower()}({e.label})"


def print_table():
    print("=== TABEL EVENT ===")
    print(f"{'No':<3} {'Proses':<7} {'Tipe':<9} {'Label':<6} {'Perhitungan':<14} TS")
    for e in LOG:
        print(f"{e.eid+1:<3} P{e.pid:<6} {e.kind:<9} {e.label:<6} {e.calc:<14} {e.ts}")


def verify():
    print("\n=== VERIFIKASI 1: Clock Condition (a -> b  =>  C(a) < C(b)) ===")
    ok = True
    for a, b in HB:
        good = LOG[a].ts < LOG[b].ts
        ok &= good
        print(f"{name(LOG[a]):<18} (ts={LOG[a].ts}) -> {name(LOG[b]):<18} (ts={LOG[b].ts})  {'OK' if good else 'LANGGAR'}")
    print("Hasil:", "KONSISTEN" if ok else "TIDAK KONSISTEN")

    # transitive closure happens-before
    n = len(LOG)
    reach = [[False] * n for _ in range(n)]
    for a, b in HB:
        reach[a][b] = True
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if reach[i][k] and reach[k][j]:
                    reach[i][j] = True

    print("\n=== VERIFIKASI 2: Total Ordering (sort by ts, tie-break pid) ===")
    order = sorted(LOG, key=lambda e: (e.ts, e.pid))
    for i, e in enumerate(order, 1):
        print(f"{i:>2}. (ts={e.ts}, P{e.pid}) {name(e)}")
    # pastikan urutan total tidak melanggar happens-before
    pos = {e.eid: i for i, e in enumerate(order)}
    ok2 = all(pos[a] < pos[b] for a in range(n) for b in range(n) if reach[a][b])
    print("Total order menghormati happens-before:", "YA" if ok2 else "TIDAK")

    print("\n=== VERIFIKASI 3: Event Concurrent dengan TS sama (converse tidak berlaku) ===")
    for a in range(n):
        for b in range(a + 1, n):
            if not reach[a][b] and not reach[b][a] and LOG[a].ts == LOG[b].ts:
                print(f"{name(LOG[a])} || {name(LOG[b])}  sama-sama ts={LOG[a].ts}, concurrent")


if __name__ == "__main__":
    simulate()
    print_table()
    verify()
