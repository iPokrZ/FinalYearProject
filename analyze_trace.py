import sys
from pathlib import Path
import math
import xml.etree.ElementTree as ET
from sklearn.preprocessing import StandardScaler
import numpy as np
import joblib
import pandas as pd

# ========= GLOBAL OUTPUT BUFFER =========
log_lines = []


def log(msg: str) -> None:
    log_lines.append(msg)


# ========= HELPERS =========

def build_unit_cost_table(root) -> dict:
    utt = root.find(".//rts.units.UnitTypeTable")
    cost_table = {}
    if utt is not None:
        for ut in utt.findall("rts.units.UnitType"):
            name = ut.get("name")
            cost = ut.get("cost")
            if name is not None and cost is not None:
                cost_table[name] = int(cost)
    return cost_table


def count_units_built(root, player_id: str) -> dict:
    entries = root.find("entries")
    counts = {}
    if entries is None:
        return counts

    seen_ids = set()
    for entry in entries.findall("rts.TraceEntry"):
        pgs = entry.find("rts.PhysicalGameState")
        if pgs is None:
            continue
        units = pgs.find("units")
        if units is None:
            continue

        for u in units.findall("rts.units.Unit"):
            if u.get("player") != player_id:
                continue
            uid = u.get("ID")
            if uid is None or uid in seen_ids:
                continue
            seen_ids.add(uid)
            utype = u.get("type")
            if utype is None:
                continue
            counts[utype] = counts.get(utype, 0) + 1
    return counts


def get_player_resources(entry, player_id: str) -> int:
    pgs = entry.find("rts.PhysicalGameState")
    if pgs is None:
        return 0
    players = pgs.find("players")
    if players is None:
        return 0
    for p in players.findall("rts.Player"):
        if p.get("ID") == player_id:
            return int(p.get("resources", "0"))
    return 0


def total_map_resources(root) -> int:
    entries = root.find("entries")
    if entries is None:
        return 0
    first_entry = next(iter(entries.findall("rts.TraceEntry")), None)
    if first_entry is None:
        return 0

    pgs = first_entry.find("rts.PhysicalGameState")
    if pgs is None:
        return 0
    units = pgs.find("units")
    if units is None:
        return 0

    total = 0
    for u in units.findall("rts.units.Unit"):
        if u.get("type") == "Resource" and u.get("player") == "-1":
            total += int(u.get("resources", "0"))
    return total


# ========= MAIN ANALYSIS FUNCTIONS =========

def first_barracks_time(root, player_id: str) -> None:
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    first_time = None
    for entry in entries.findall("rts.TraceEntry"):
        t = entry.get("time")
        pgs = entry.find("rts.PhysicalGameState")
        if pgs is None:
            continue
        units = pgs.find("units")
        if units is None:
            continue

        for u in units.findall("rts.units.Unit"):
            if u.get("type") == "Barracks" and u.get("player") == player_id:
                first_time = t
                break
        if first_time is not None:
            break

    if first_time is None:
        log(f"Player {player_id} never has a Barracks in this trace.")
    else:
        log(f"Player {player_id} first has a Barracks at trace time = {first_time}")


def barracks_count(root, player_id: str) -> None:
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    barracks_ids = set()
    for entry in entries.findall("rts.TraceEntry"):
        pgs = entry.find("rts.PhysicalGameState")
        if pgs is None:
            continue
        units = pgs.find("units")
        if units is None:
            continue

        for u in units.findall("rts.units.Unit"):
            if u.get("type") == "Barracks" and u.get("player") == player_id:
                uid = u.get("ID")
                if uid is not None:
                    barracks_ids.add(uid)

    log(f"Player {player_id} built {len(barracks_ids)} Barracks in this trace.")


def harvested_resources(root, player_id: str) -> None:
    cost_table = build_unit_cost_table(root)
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    all_entries = entries.findall("rts.TraceEntry")
    if not all_entries:
        log("Trace has no entries.")
        return

    first_entry = all_entries[0]
    last_entry = all_entries[-1]

    r_initial = get_player_resources(first_entry, player_id)
    r_final = get_player_resources(last_entry, player_id)

    built_counts = count_units_built(root, player_id)

    total_spent = 0
    for unit_type, n in built_counts.items():
        cost = cost_table.get(unit_type, 0)
        total_spent += cost * n

    harvested = (r_final - r_initial) + total_spent

    log(f"Player {player_id} approximately harvested {harvested} resources in this game.")
    log(f"  (initial={r_initial}, final={r_final}, spent={total_spent})")


def harvested_resources_percent(root, player_id: str) -> None:
    cost_table = build_unit_cost_table(root)
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    all_entries = entries.findall("rts.TraceEntry")
    if not all_entries:
        log("Trace has no entries.")
        return

    first_entry = all_entries[0]
    last_entry = all_entries[-1]

    r_initial = get_player_resources(first_entry, player_id)
    r_final = get_player_resources(last_entry, player_id)

    built_counts = count_units_built(root, player_id)
    total_spent = 0
    for unit_type, n in built_counts.items():
        cost = cost_table.get(unit_type, 0)
        total_spent += cost * n

    harvested = (r_final - r_initial) + total_spent
    total_initial_resources = total_map_resources(root)

    if total_initial_resources > 0:
        percent = 100.0 * harvested / total_initial_resources
    else:
        percent = 0.0

    log(f"Total initial resources on map: {total_initial_resources}")
    log(f"Player {player_id} approx harvested: {harvested}")
    log(f"Player {player_id} harvested ~{percent:.2f}% of all resources on the map.")


def workers_built(root, player_id: str) -> None:
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    seen_ids = set()
    workers_built_count = 0

    for entry in entries.findall("rts.TraceEntry"):
        pgs = entry.find("rts.PhysicalGameState")
        if pgs is None:
            continue
        units = pgs.find("units")
        if units is None:
            continue

        for u in units.findall("rts.units.Unit"):
            if u.get("player") != player_id:
                continue
            if u.get("type") != "Worker":
                continue
            uid = u.get("ID")
            if uid is None or uid in seen_ids:
                continue
            seen_ids.add(uid)
            workers_built_count += 1

    log(f"Player {player_id} built {workers_built_count} Workers in this trace.")


def workers_built_milestones(root, player_id: str) -> None:
    milestones = [100, 200, 400, 800]
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    milestone_counts = {m: None for m in milestones}
    seen_ids = set()
    workers_built_count = 0

    for entry in entries.findall("rts.TraceEntry"):
        t_str = entry.get("time")
        if t_str is None:
            continue
        t = int(t_str)

        pgs = entry.find("rts.PhysicalGameState")
        if pgs is None:
            continue
        units = pgs.find("units")
        if units is None:
            continue

        for u in units.findall("rts.units.Unit"):
            if u.get("player") != player_id:
                continue
            if u.get("type") != "Worker":
                continue
            uid = u.get("ID")
            if uid is None or uid in seen_ids:
                continue
            seen_ids.add(uid)
            workers_built_count += 1

        for m in milestones:
            if milestone_counts[m] is None and t >= m:
                milestone_counts[m] = workers_built_count

    log(f"Workers built by player {player_id} at milestones (cumulative):")
    for m in milestones:
        if milestone_counts[m] is not None:
            log(f"  time >= {m}: {milestone_counts[m]} Workers")
        else:
            log(f"  time >= {m}: (milestone not reached in this trace)")


def game_length_ticks(root) -> None:
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    all_entries = entries.findall("rts.TraceEntry")
    if not all_entries:
        log("Trace has no entries.")
        return

    last_entry = all_entries[-1]
    t_str = last_entry.get("time", "0")
    try:
        t = int(t_str)
    except ValueError:
        t = 0

    log(f"Game length: {t} ticks")


def player_won(root, player_id: str, enemy_id: str) -> None:
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    all_entries = entries.findall("rts.TraceEntry")
    if not all_entries:
        log("Trace has no entries.")
        return

    last_entry = all_entries[-1]
    pgs = last_entry.find("rts.PhysicalGameState")
    if pgs is None:
        log("No PhysicalGameState in last entry.")
        return

    units = pgs.find("units")
    if units is None:
        log("No units section in last entry.")
        return

    has_me = False
    has_enemy = False
    for u in units.findall("rts.units.Unit"):
        p = u.get("player")
        if p == player_id:
            has_me = True
        elif p == enemy_id:
            has_enemy = True

    if has_me and not has_enemy:
        log(f"Player {player_id}: WIN")
    elif has_enemy and not has_me:
        log(f"Player {player_id}: LOSS")
    else:
        log(f"Player {player_id}: DRAW/UNDECIDED (both or neither have units)")


def combat_units_built(root, player_id: str) -> None:
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    seen_ids = set()
    light = heavy = ranged = 0

    for entry in entries.findall("rts.TraceEntry"):
        pgs = entry.find("rts.PhysicalGameState")
        if pgs is None:
            continue
        units = pgs.find("units")
        if units is None:
            continue

        for u in units.findall("rts.units.Unit"):
            if u.get("player") != player_id:
                continue
            utype = u.get("type")
            if utype not in ("Light", "Heavy", "Ranged"):
                continue
            uid = u.get("ID")
            if uid is None or uid in seen_ids:
                continue
            seen_ids.add(uid)
            if utype == "Light":
                light += 1
            elif utype == "Heavy":
                heavy += 1
            elif utype == "Ranged":
                ranged += 1

    log(f"Player {player_id} built in total:")
    log(f"  Light units : {light}")
    log(f"  Heavy units : {heavy}")
    log(f"  Ranged units: {ranged}")


def first_attack_time(root, player_id: str) -> None:
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    first_time = None
    for entry in entries.findall("rts.TraceEntry"):
        t = entry.get("time")
        if t is None:
            continue

        pgs = entry.find("rts.PhysicalGameState")
        if pgs is None:
            continue
        units_node = pgs.find("units")
        if units_node is None:
            continue

        unit_player = {}
        for u in units_node.findall("rts.units.Unit"):
            uid = u.get("ID")
            p = u.get("player")
            if uid is not None:
                unit_player[uid] = p

        actions_node = entry.find("actions")
        if actions_node is None:
            continue

        for a in actions_node.findall("action"):
            uid = a.get("unitID")
            if uid is None:
                continue
            if unit_player.get(uid) != player_id:
                continue
            ua = a.find("UnitAction")
            if ua is None:
                continue
            if ua.get("type") == "5":
                first_time = t
                break
        if first_time is not None:
            break

    if first_time is None:
        log(f"Player {player_id} never issues an ATTACK action in this trace.")
    else:
        log(f"Player {player_id} first ATTACK action at trace time = {first_time}")


def total_attacks(root, player_id: str) -> int:
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return 0

    attack_count = 0
    for entry in entries.findall("rts.TraceEntry"):
        pgs = entry.find("rts.PhysicalGameState")
        if pgs is None:
            continue
        units_node = pgs.find("units")
        if units_node is None:
            continue

        unit_player = {}
        for u in units_node.findall("rts.units.Unit"):
            uid = u.get("ID")
            p = u.get("player")
            if uid is not None:
                unit_player[uid] = p

        actions_node = entry.find("actions")
        if actions_node is None:
            continue

        for a in actions_node.findall("action"):
            uid = a.get("unitID")
            if uid is None:
                continue
            if unit_player.get(uid) != player_id:
                continue
            ua = a.find("UnitAction")
            if ua is None:
                continue
            if ua.get("type") == "5":
                attack_count += 1

    log(f"Player {player_id} issued {attack_count} ATTACK actions in this trace.")
    return attack_count


def attacks_per_trace(root, player_id: str) -> None:
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    all_entries = entries.findall("rts.TraceEntry")
    num_entries = len(all_entries)
    if num_entries == 0:
        log("Trace has no entries.")
        return

    total_attacks_count = 0
    for entry in all_entries:
        pgs = entry.find("rts.PhysicalGameState")
        if pgs is None:
            continue
        units_node = pgs.find("units")
        if units_node is None:
            continue

        unit_player = {}
        for u in units_node.findall("rts.units.Unit"):
            uid = u.get("ID")
            p = u.get("player")
            if uid is not None:
                unit_player[uid] = p

        actions_node = entry.find("actions")
        if actions_node is None:
            continue

        for a in actions_node.findall("action"):
            uid = a.get("unitID")
            if uid is None:
                continue
            if unit_player.get(uid) != player_id:
                continue
            ua = a.find("UnitAction")
            if ua is None:
                continue
            if ua.get("type") == "5":
                total_attacks_count += 1

    attacks_per_entry = total_attacks_count / num_entries
    log(f"Player {player_id} issued {total_attacks_count} ATTACK actions in total.")
    log(f"Number of trace entries: {num_entries}")
    log(f"Average ATTACKs per trace entry: {attacks_per_entry:.4f}")


def max_attacks_in_single_trace(root, player_id: str) -> None:
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    max_attacks = 0
    max_time = None

    for entry in entries.findall("rts.TraceEntry"):
        t = entry.get("time")
        if t is None:
            continue

        pgs = entry.find("rts.PhysicalGameState")
        if pgs is None:
            continue
        units_node = pgs.find("units")
        if units_node is None:
            continue

        unit_player = {}
        for u in units_node.findall("rts.units.Unit"):
            uid = u.get("ID")
            p = u.get("player")
            if uid is not None:
                unit_player[uid] = p

        actions_node = entry.find("actions")
        if actions_node is None:
            continue

        attacks_this_entry = 0
        for a in actions_node.findall("action"):
            uid = a.get("unitID")
            if uid is None:
                continue
            if unit_player.get(uid) != player_id:
                continue
            ua = a.find("UnitAction")
            if ua is None:
                continue
            if ua.get("type") == "5":
                attacks_this_entry += 1

        if attacks_this_entry > max_attacks:
            max_attacks = attacks_this_entry
            max_time = t

    if max_time is None:
        log(f"Player {player_id} never issues an ATTACK action in this trace.")
    else:
        log(f"Max ATTACKs by player {player_id} in a single trace entry: {max_attacks}")
        log(f"Occurred at trace time = {max_time}")


def avg_distance_to_enemy_base(root, player_id: str, enemy_id: str) -> None:
    milestones = [100, 200, 400, 800]
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    all_entries = entries.findall("rts.TraceEntry")
    if not all_entries:
        log("Trace has no entries.")
        return

    enemy_base_pos = None
    for entry in all_entries:
        pgs = entry.find("rts.PhysicalGameState")
        if pgs is None:
            continue
        units = pgs.find("units")
        if units is None:
            continue
        for u in units.findall("rts.units.Unit"):
            if u.get("type") == "Base" and u.get("player") == enemy_id:
                x = u.get("x")
                y = u.get("y")
                if x is not None and y is not None:
                    enemy_base_pos = (int(x), int(y))
                    break
        if enemy_base_pos is not None:
            break

    if enemy_base_pos is None:
        log(f"Could not find enemy base (player {enemy_id} Base) in trace.")
        return

    ex, ey = enemy_base_pos
    results = {m: (None, None) for m in milestones}

    for m in milestones:
        entry_for_m = None
        for entry in all_entries:
            t_str = entry.get("time")
            if t_str is None:
                continue
            t = int(t_str)
            if t >= m:
                entry_for_m = (t, entry)
                break
        if entry_for_m is None:
            continue

        t, entry = entry_for_m
        pgs = entry.find("rts.PhysicalGameState")
        if pgs is None:
            continue
        units = pgs.find("units")
        if units is None:
            continue

        distances = []
        for u in units.findall("rts.units.Unit"):
            if u.get("player") != player_id:
                continue
            ux = u.get("x")
            uy = u.get("y")
            if ux is None or uy is None:
                continue
            ux = int(ux)
            uy = int(uy)
            d = math.sqrt((ux - ex) ** 2 + (uy - ey) ** 2)
            distances.append(d)

        if distances:
            avg_d = sum(distances) / len(distances)
            results[m] = (avg_d, t)
        else:
            results[m] = (None, t)

    log(f"Average distance of player-{player_id} units to enemy base (player {enemy_id} Base):")
    log(f"Enemy base at: {enemy_base_pos}")
    for m in milestones:
        avg_d, t = results[m]
        if t is None:
            log(f"  time >= {m}: milestone not reached in this trace")
        elif avg_d is None:
            log(f"  time >= {m} (first time={t}): no player-{player_id} units present")
        else:
            log(f"  time >= {m} (first time={t}): avg distance = {avg_d:.3f}")


def combat_units_milestones(root, player_id: str) -> None:
    milestones = [100, 200, 400, 800]
    entries = root.find("entries")
    if entries is None:
        log("No <entries> section found.")
        return

    all_entries = entries.findall("rts.TraceEntry")
    if not all_entries:
        log("Trace has no entries.")
        return

    results = {}
    for m in milestones:
        chosen = None
        for entry in all_entries:
            t_str = entry.get("time")
            if t_str is None:
                continue
            t = int(t_str)
            if t >= m:
                chosen = (t, entry)
                break
        if chosen is None:
            results[m] = None
            continue

        t, entry = chosen
        pgs = entry.find("rts.PhysicalGameState")
        if pgs is None:
            results[m] = (t, 0, 0, 0)
            continue
        units = pgs.find("units")
        if units is None:
            results[m] = (t, 0, 0, 0)
            continue

        light = heavy = ranged = 0
        for u in units.findall("rts.units.Unit"):
            if u.get("player") != player_id:
                continue
            utype = u.get("type")
            if utype == "Light":
                light += 1
            elif utype == "Heavy":
                heavy += 1
            elif utype == "Ranged":
                ranged += 1

        results[m] = (t, light, heavy, ranged)

    log(f"Player {player_id} combat units at milestones:")
    for m in milestones:
        val = results[m]
        if val is None:
            log(f"  time >= {m}: milestone not reached in this trace")
        else:
            t, light, heavy, ranged = val
            log(f"  time >= {m} (first time={t}): Light={light}, Heavy={heavy}, Ranged={ranged}")


# ========= MASTER CALLER =========

def analyze_trace(trace_file_path: str, player_id: str = "0", enemy_id: str = "1") -> str:
    global log_lines
    log_lines = []

    try:
        tree = ET.parse(trace_file_path)
        root = tree.getroot()

        log(f"=== Analyzing trace: {Path(trace_file_path).name}, player {player_id} vs {enemy_id} ===")
        first_barracks_time(root, player_id)
        barracks_count(root, player_id)
        combat_units_milestones(root, player_id)
        avg_distance_to_enemy_base(root, player_id, enemy_id)
        max_attacks_in_single_trace(root, player_id)
        attacks_per_trace(root, player_id)
        first_attack_time(root, player_id)
        combat_units_built(root, player_id)
        game_length_ticks(root)
        player_won(root, player_id, enemy_id)
        workers_built_milestones(root, player_id)
        workers_built(root, player_id)
        harvested_resources(root, player_id)
        harvested_resources_percent(root, player_id)

        return "\n".join(log_lines)

    except FileNotFoundError:
        return f"ERROR: File not found: {trace_file_path}"
    except ET.ParseError as e:
        return f"ERROR: XML parse error: {e}"
    except Exception as e:
        return f"ERROR: {e}"


# ========= MAIN ENTRY POINT =========

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR: No trace file provided")
        print("Usage: python analyze_trace.py <trace_file_path> [player_id] [enemy_id]")
        sys.exit(1)

    trace_file = sys.argv[1]
    # default: analyze player 1 vs 0
    player_id = sys.argv[2] if len(sys.argv) > 2 else "0"
    enemy_id = sys.argv[3] if len(sys.argv) > 3 else "1"

    result = analyze_trace(trace_file, player_id, enemy_id)
    # print(result)

    # write to file next to the trace
    trace_path = Path(trace_file)
    out_name = f"{trace_path.stem}_analysis_p{player_id}.txt"
    out_path = trace_path.with_name(out_name)
    try:
        out_path.write_text(result, encoding="utf-8")
        # print(f"\nAnalysis written to: {out_path}")
    except Exception as e:
        print(f"\nERROR writing analysis file: {e}")

# SECOND PART:

import re

# Path to a SINGLE analysis file produced by analyze_trace.py
log_path = Path(out_path)  # change to your actual file

COLS = [
    "FirstBarracks",
    "NumBarracks",
    "Light100",
    "Heavy100",
    "Ranged100",
    "Light200",
    "Heavy200",
    "Ranged200",
    "Light400",
    "Heavy400",
    "Ranged400",
    "Light800",
    "Heavy800",
    "Ranged800",
    "AvgDist100",
    "AvgDist200",
    "AvgDist400",
    "AvgDist800",
    "MaxAttacksSingleTrace",
    "TimeMaxAttacks",
    "TotalAttacks",
    "AvgAttacksPerTrace",
    "FirstAttackTime",
    "TotalLight",
    "TotalHeavy",
    "TotalRanged",
    "GameLength",
    "PlayerWin",
    "Workers100",
    "Workers200",
    "Workers400",
    "Workers800",
    "TotalWorkers",
    "PercentMapHarvested",
]

MILESTONES = [100, 200, 400, 800]


def carry_forward_milestones(data: dict) -> None:
    # Workers: carry forward, then fall back to TotalWorkers
    last = None
    for t in MILESTONES:
        key = f"Workers{t}"
        v = data.get(key, -1)
        if v != -1:
            last = v
        else:
            if last is not None:
                data[key] = last
    total_workers = data.get("TotalWorkers", -1)
    if total_workers != -1:
        for t in MILESTONES:
            key = f"Workers{t}"
            if data.get(key, -1) == -1:
                data[key] = total_workers
    else:
        for t in MILESTONES:
            key = f"Workers{t}"
            if data.get(key, -1) == -1:
                data[key] = 0

    # Combat units: Light / Heavy / Ranged
    for unit in ("Light", "Heavy", "Ranged"):
        last = None
        for t in MILESTONES:
            key = f"{unit}{t}"
            v = data.get(key, -1)
            if v != -1:
                last = v
            else:
                if last is not None:
                    data[key] = last
        total_key = f"Total{unit}"
        total_val = data.get(total_key, -1)
        if total_val != -1:
            for t in MILESTONES:
                key = f"{unit}{t}"
                if data.get(key, -1) == -1:
                    data[key] = total_val
        else:
            for t in MILESTONES:
                key = f"{unit}{t}"
                if data.get(key, -1) == -1:
                    data[key] = 0

    # AvgDist at milestones: carry forward last seen distance
    last = None
    for t in MILESTONES:
        key = f"AvgDist{t}"
        v = data.get(key, -1)
        if v != -1:
            last = v
        else:
            if last is not None:
                data[key] = last
    # If still missing at all milestones, set to 0
    for t in MILESTONES:
        key = f"AvgDist{t}"
        if data.get(key, -1) == -1:
            data[key] = 0.0


def parse_single_file(text: str) -> dict:
    # assume "player X vs Y" is in the first line
    first_line = text.splitlines()[0].strip()
    m_pid = re.search(r"player\s+(\d+)\s+vs\s+(\d+)", first_line)
    if m_pid:
        player_id = int(m_pid.group(1))
    else:
        player_id = 1  # default to player 1 if not found

    data = {k: -1 for k in COLS}
    data["FirstBarracks"] = 0  # default if never seen

    for line in text.splitlines():
        line = line.strip()

        m = re.search(rf"Player {player_id} first has a Barracks at trace time = (\d+)", line)
        if m:
            data["FirstBarracks"] = int(m.group(1))

        m = re.search(rf"Player {player_id} built (\d+) Barracks", line)
        if m:
            data["NumBarracks"] = int(m.group(1))

        m = re.search(r"time >= (\d+) \(first time=\d+\): Light=(\d+), Heavy=(\d+), Ranged=(\d+)", line)
        if m:
            t, L, H, R = map(int, m.groups())
            if t in (100, 200, 400, 800):
                data[f"Light{t}"] = L
                data[f"Heavy{t}"] = H
                data[f"Ranged{t}"] = R

        m = re.search(r"time >= (\d+) \(first time=\d+\): avg distance = ([0-9.]+)", line)
        if m:
            t = int(m.group(1))
            if t in (100, 200, 400, 800):
                data[f"AvgDist{t}"] = float(m.group(2))

        m = re.search(rf"Max ATTACKs by player {player_id} in a single trace entry: (\d+)", line)
        if m:
            data["MaxAttacksSingleTrace"] = int(m.group(1))

        m = re.search(r"Occurred at trace time = (\d+)", line)
        if m:
            data["TimeMaxAttacks"] = int(m.group(1))

        m = re.search(rf"Player {player_id} issued (\d+) ATTACK actions in total", line)
        if m:
            data["TotalAttacks"] = int(m.group(1))

        m = re.search(r"Average ATTACKs per trace entry: ([0-9.]+)", line)
        if m:
            data["AvgAttacksPerTrace"] = float(m.group(1))

        m = re.search(rf"Player {player_id} first ATTACK action at trace time = (\d+)", line)
        if m:
            data["FirstAttackTime"] = int(m.group(1))

        m = re.search(r"Light units\s*:\s*(\d+)", line)
        if m:
            data["TotalLight"] = int(m.group(1))
        m = re.search(r"Heavy units\s*:\s*(\d+)", line)
        if m:
            data["TotalHeavy"] = int(m.group(1))
        m = re.search(r"Ranged units\s*:\s*(\d+)", line)
        if m:
            data["TotalRanged"] = int(m.group(1))

        m = re.search(r"Game length:\s*(\d+)\s*ticks", line)
        if m:
            data["GameLength"] = int(m.group(1))

        if f"Player {player_id}: WIN" in line:
            data["PlayerWin"] = 1
        elif f"Player {player_id}: LOSS" in line:
            data["PlayerWin"] = 0
        elif f"Player {player_id}: DRAW" in line:
            data["PlayerWin"] = 0.5

        m = re.search(r"time >= (\d+): (\d+) Workers", line)
        if m:
            t = int(m.group(1))
            if t in (100, 200, 400, 800):
                data[f"Workers{t}"] = int(m.group(2))

        m = re.search(rf"Player {player_id} built (\d+) Workers in this trace", line)
        if m:
            data["TotalWorkers"] = int(m.group(1))

        m = re.search(rf"Player {player_id} harvested ~([0-9.]+)% of all resources", line)
        if m:
            data["PercentMapHarvested"] = float(m.group(1))

    carry_forward_milestones(data)

    for k in COLS:
        if isinstance(data[k], (int, float)) and data[k] == -1:
            data[k] = 0

    return data

# ==== main for single file: build standardized row for Java ====

# 1) Read analysis text and parse features
text = log_path.read_text(encoding="utf-8")
data = parse_single_file(text)          # dict: key -> value

# data is your dict from parse_single_file
row_values = [data[k] for k in COLS]

# 1-row DataFrame with correct feature names
# x_df = pd.DataFrame([row_values], columns=COLS)

# Transform
# x_scaled = scaler.transform(x_df)


# 5) Write standardized row for Java
out_csv_java = Path("single_trace_features.csv")
# no scaler load here
with out_csv_java.open("w", encoding="utf-8") as f:
    f.write(",".join(str(v) for v in row_values) + "\n")
