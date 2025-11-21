from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set, Optional
import sys
import heapq

# --- Data Structures ---

@dataclass(frozen=True, order=True)
class Coord:
    x: int
    y: int
    def __repr__(self) -> str: return f"{self.x} {self.y}"

@dataclass
class Tile:
    region_id: int
    type: int
    tracks_owner: int
    inked: bool
    instability: int
    is_town: bool = False # <--- Added flag to prevent building on towns
    active_conn_ids: Set[Tuple[int, int]] = field(default_factory=set)

@dataclass
class Town:
    id: int
    coord: Coord
    desired_connections: List[int]

@dataclass
class Region:
    id: int
    instability: int
    inked: bool
    coords: List[Coord]
    has_town: bool

class Game:
    def __init__(self):
        self.my_id = 0
        self.width = 0
        self.height = 0
        self.tiles: List[List[Tile]] = []
        self.towns: Dict[int, Town] = {} 
        self.town_list: List[Town] = []
        self.region_by_id: Dict[int, Region] = {}
        
        self.persistent_disrupt_target: Optional[int] = None
        
        # Costs: Plains=1, River=2, Mountain=3, POI=3
        self.COSTS = (1, 2, 3, 3) 
        self.DIRS = ((0, 1), (1, 0), (0, -1), (-1, 0))
        self.my_track_coords = set()
        self.all_town_coords = set()

    def init(self):
        try:
            line1 = input().split()
            if not line1: return 
            self.my_id = int(line1[0])
            self.width = int(input())
            self.height = int(input())

            for y in range(self.height):
                row = []
                for x in range(self.width):
                    rid, ttype = map(int, input().split())
                    if rid not in self.region_by_id:
                        self.region_by_id[rid] = Region(rid, 0, False, [], False)
                    self.region_by_id[rid].coords.append(Coord(x, y))
                    # Initialize Tile
                    row.append(Tile(rid, ttype, -1, False, 0, is_town=False))
                self.tiles.append(row)

            town_count = int(input())
            for _ in range(town_count):
                parts = input().split()
                tid, tx, ty = int(parts[0]), int(parts[1]), int(parts[2])
                conn_str = parts[3]
                targets = []
                if conn_str != "x":
                    targets = [int(x) for x in conn_str.split(",")]
                
                town = Town(tid, Coord(tx, ty), targets)
                self.towns[tid] = town
                self.town_list.append(town)
                
                # Mark metadata
                self.region_by_id[self.tiles[ty][tx].region_id].has_town = True
                self.all_town_coords.add((tx, ty))
                # IMPORTANT: Mark the tile as a town
                self.tiles[ty][tx].is_town = True

        except EOFError:
            pass

    def parse(self):
        try:
            _my_score = int(input())
            _foe_score = int(input())
            
            self.my_track_coords.clear()
            
            for y in range(self.height):
                for x in range(self.width):
                    raw = input().split()
                    owner = int(raw[0])
                    instability = int(raw[1])
                    inked = (raw[2] == "1")
                    conns_str = raw[3]
                    
                    t = self.tiles[y][x]
                    t.tracks_owner = owner
                    t.instability = instability
                    t.inked = inked
                    
                    r = self.region_by_id[t.region_id]
                    r.instability = instability
                    r.inked = inked
                    
                    t.active_conn_ids = set()
                    if conns_str != "x":
                        for pair in conns_str.split(","):
                            u, v = map(int, pair.split("-"))
                            t.active_conn_ids.add((u, v))

                    if owner == self.my_id:
                        self.my_track_coords.add((x, y))
        except EOFError:
            sys.exit(0)

    # --- Optimized Pathfinding ---

    def get_best_path(self, start_town_id: int, end_town_id: int) -> Dict:
        start_node = self.towns[start_town_id].coord
        end_node = self.towns[end_town_id].coord
        target_pos = (end_node.x, end_node.y)
        
        pq = [(0, 0, start_node.x, start_node.y)]
        min_costs = {(start_node.x, start_node.y): 0}
        came_from = {}

        while pq:
            cost, steps, x, y = heapq.heappop(pq)
            
            if cost > min_costs[(x, y)]:
                continue
            
            if x == target_pos[0] and y == target_pos[1]:
                # Reconstruct
                full_path = []
                curr = (x, y)
                while curr:
                    full_path.append(Coord(curr[0], curr[1]))
                    curr = came_from.get(curr)
                full_path.reverse()
                
                unbuilt = []
                missing_cost = 0
                total_points = 0
                
                for coord in full_path[1:-1]: # Exclude start/end towns
                    t = self.tiles[coord.y][coord.x]
                    total_points += 1
                    
                    # FIX: Don't build on towns, even intermediate ones
                    if t.is_town:
                        continue
                        
                    if t.tracks_owner == -1:
                        unbuilt.append(coord)
                        missing_cost += self.COSTS[t.type]
                
                return {
                    "found": True,
                    "full_path": full_path,
                    "unbuilt": unbuilt,
                    "missing_cost": missing_cost,
                    "total_points": total_points,
                    "from": start_town_id,
                    "to": end_town_id
                }

            for dx, dy in self.DIRS:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.width and 0 <= ny < self.height): continue
                
                tile = self.tiles[ny][nx]
                if tile.inked: continue
                
                step_cost = 0
                is_obstacle = False
                
                # FIX: Entering any town costs 0 paint (valid connection node)
                if tile.is_town:
                    step_cost = 0
                elif tile.tracks_owner == -1:
                    step_cost = self.COSTS[tile.type]
                elif tile.tracks_owner == self.my_id or tile.tracks_owner == 2:
                    step_cost = 0
                else:
                    is_obstacle = True 
                
                if not is_obstacle:
                    new_cost = cost + step_cost
                    if (nx, ny) not in min_costs or new_cost < min_costs[(nx, ny)]:
                        min_costs[(nx, ny)] = new_cost
                        came_from[(nx, ny)] = (x, y)
                        heapq.heappush(pq, (new_cost, steps + 1, nx, ny))
        
        return {"found": False}

    # --- Disruption ---

    def get_disruption_target(self) -> Optional[int]:
        foe_id = 1 - self.my_id
        
        if self.persistent_disrupt_target is not None:
            rid = self.persistent_disrupt_target
            r = self.region_by_id.get(rid)
            valid = False
            if r and not r.inked:
                enemy_presence = sum(1 for c in r.coords if self.tiles[c.y][c.x].tracks_owner == foe_id)
                if enemy_presence > 0:
                    valid = True
            if valid: return rid
            else: self.persistent_disrupt_target = None
        
        best_rid = None
        best_score = 0
        
        for rid, region in self.region_by_id.items():
            if region.inked or region.has_town: continue
            
            foe_tracks = 0
            foe_conn_val = 0
            my_conn_val = 0
            
            for c in region.coords:
                t = self.tiles[c.y][c.x]
                if t.tracks_owner == foe_id:
                    foe_tracks += 1
                    if t.active_conn_ids: foe_conn_val += len(t.active_conn_ids)
                elif t.tracks_owner == self.my_id:
                    if t.active_conn_ids: my_conn_val += len(t.active_conn_ids)

            if foe_tracks == 0: continue
            if my_conn_val > foe_conn_val + 1: continue

            score = (foe_conn_val * 50) + (foe_tracks * 5) + (region.instability * 10)
            
            if score > best_score:
                best_score = score
                best_rid = rid
        
        if best_rid is not None:
            self.persistent_disrupt_target = best_rid
            return best_rid
        return None

    # --- Smart Building ---

    def get_smart_actions(self) -> List[str]:
        paint = 3
        actions = []
        built_this_turn = set()
        
        candidates = []
        for town in self.town_list:
            for target_id in town.desired_connections:
                res = self.get_best_path(town.id, target_id)
                if res["found"]:
                    candidates.append(res)
        
        if not candidates: return []

        while paint > 0:
            tile_scores = {}
            
            active_cands = [c for c in candidates if c["missing_cost"] > 0]
            if not active_cands: break
            
            for cand in active_cands:
                points = cand["total_points"]
                cost = cand["missing_cost"]
                
                if cost <= paint:
                    base_prio = points * 1000
                else:
                    base_prio = (points * 10) / (cost + 0.1)
                
                for coord in cand["unbuilt"]:
                    pos = (coord.x, coord.y)
                    if pos in built_this_turn: continue
                    
                    t_cost = self.COSTS[self.tiles[coord.y][coord.x].type]
                    if t_cost > paint: continue
                    
                    tile_scores[pos] = tile_scores.get(pos, 0.0) + base_prio

            if not tile_scores: break
            
            best_pos = None
            best_final_score = -1
            
            check_set = self.my_track_coords | self.all_town_coords | built_this_turn
            
            for pos, raw_score in tile_scores.items():
                x, y = pos
                
                is_adj = False
                for dx, dy in self.DIRS:
                    if (x+dx, y+dy) in check_set:
                        is_adj = True
                        break
                
                final_score = raw_score * (1.5 if is_adj else 1.0)
                cost = self.COSTS[self.tiles[y][x].type]
                metric = final_score / cost
                
                if metric > best_final_score:
                    best_final_score = metric
                    best_pos = pos
            
            if best_pos:
                bx, by = best_pos
                cost = self.COSTS[self.tiles[by][bx].type]
                actions.append(f"PLACE_TRACKS {bx} {by}")
                paint -= cost
                built_this_turn.add(best_pos)
                
                for cand in candidates:
                    idx_to_remove = -1
                    for i, uc in enumerate(cand["unbuilt"]):
                        if uc.x == bx and uc.y == by:
                            idx_to_remove = i
                            break
                    if idx_to_remove != -1:
                        cand["unbuilt"].pop(idx_to_remove)
                        cand["missing_cost"] -= cost
            else:
                break
                
        return actions

    def turn(self):
        builds = self.get_smart_actions()
        disrupt = self.get_disruption_target()
        
        cmds = builds[:]
        if disrupt is not None:
            cmds.append(f"DISRUPT {disrupt}")
        
        if cmds:
            print(";".join(cmds))
        else:
            print("WAIT")

def main():
    game = Game()
    game.init()
    while True:
        game.parse()
        game.turn()

if __name__ == "__main__":
    main()