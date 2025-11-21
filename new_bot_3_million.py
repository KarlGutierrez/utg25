from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Set, Optional
import sys
import heapq

@dataclass(frozen=True)
class Coord:
    x: int
    y: int

    def __repr__(self) -> str:
        return f"{self.x} {self.y}"

@dataclass
class Connection:
    from_id: int
    to_id: int

@dataclass
class Tile:
    region_id: int
    type: int
    tracks_owner: int
    inked: bool
    instability: int
    part_of_active_connections: List[Connection]

@dataclass
class Town:
    id: int
    coord: Coord
    desired_connections: List[int]

@dataclass
class Grid:
    width: int
    height: int
    tiles: List[List[Tile]]

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
        self.grid = None
        self.towns = []
        self.region_by_id = {}
        self.my_score = 0
        self.foe_score = 0
        self.town_coords_set = set()
        # Type costs: PLAINS=1, RIVER=2, MOUNTAIN=3, POI=3
        self.type_costs = {0: 1, 1: 2, 2: 3, 3: 3}
        self.directions = [(-1, 0), (0, 1), (1, 0), (0, -1)]

    def get_region_at(self, coord: Coord) -> Region:
        return self.region_by_id[self.grid.tiles[coord.y][coord.x].region_id]

    def init(self):
        try:
            self.my_id = int(input())
            width = int(input())
            height = int(input())
            self.region_by_id = {}
            self.towns = []
            self.grid = Grid(width, height, tiles=[])

            for i in range(height):
                row: List[Tile] = []
                for j in range(width):
                    region_id, _type = [int(k) for k in input().split()]
                    tileData = Tile(
                        region_id,
                        _type,
                        tracks_owner=-1,
                        inked=False,
                        instability=0,
                        part_of_active_connections=[],
                    )
                    row.append(tileData)

                    if region_id not in self.region_by_id:
                        self.region_by_id[region_id] = Region(
                            region_id, instability=0, inked=False, coords=[], has_town=False
                        )
                    region = self.region_by_id[region_id]
                    region.coords.append(Coord(x=j, y=i))
                self.grid.tiles.append(row)

            town_count = int(input())
            for i in range(town_count):
                town_id, town_x, town_y, desired_connections = input().split()
                town_id = int(town_id)
                town_x = int(town_x)
                town_y = int(town_y)
                desired_connections = (
                    []
                    if desired_connections == "x"
                    else [int(x) for x in desired_connections.split(",")]
                )
                coord = Coord(town_x, town_y)
                town = Town(town_id, coord, desired_connections)
                self.towns.append(town)
                self.get_region_at(coord).has_town = True
                self.town_coords_set.add((town_x, town_y))
        except EOFError:
            pass

    def parse(self):
        try:
            self.my_score = int(input())
            self.foe_score = int(input())
            for i in range(self.grid.height):
                for j in range(self.grid.width):
                    (
                        tracks_owner,
                        instability,
                        inked,
                        part_of_active_connections,
                    ) = input().split()
                    
                    tile = self.grid.tiles[i][j]
                    tile.tracks_owner = int(tracks_owner)
                    tile.instability = int(instability)
                    tile.inked = (inked != "0")
                    
                    self.region_by_id[tile.region_id].instability = tile.instability
                    self.region_by_id[tile.region_id].inked = tile.inked
                    
                    if part_of_active_connections == "x":
                        tile.part_of_active_connections = []
                    else:
                        connections = []
                        for connection in part_of_active_connections.split(","):
                            from_id, to_id = connection.split("-")
                            connections.append(Connection(int(from_id), int(to_id)))
                        tile.part_of_active_connections = connections
        except EOFError:
            sys.exit(0)

    def find_shortest_path(self, from_town_id: int, to_town_id: int) -> tuple[List[Coord], int, int, int]:
        from_town = self.towns[from_town_id]
        to_town = self.towns[to_town_id]
        
        dest_y, dest_x = to_town.coord.y, to_town.coord.x
        start_y, start_x = from_town.coord.y, from_town.coord.x
        
        pq = [(0, 0, start_y, start_x)]
        came_from = {}
        cost_so_far = {(start_y, start_x): 0}
        came_from[(start_y, start_x)] = None
        
        tiles = self.grid.tiles
        height = self.grid.height
        width = self.grid.width
        path_found = False
        
        while pq:
            current_cost, _, y, x = heapq.heappop(pq)
            
            if y == dest_y and x == dest_x:
                path_found = True
                break
            
            if current_cost > cost_so_far.get((y, x), float('inf')):
                continue
            
            for dy, dx in self.directions:
                ny, nx = y + dy, x + dx
                if not (0 <= ny < height and 0 <= nx < width): continue
                
                tile = tiles[ny][nx]
                if tile.inked: continue
                
                move_cost = 0
                is_obstacle = False
                
                if (nx, ny) in self.town_coords_set:
                    move_cost = 0
                elif tile.tracks_owner == -1:
                    move_cost = self.type_costs[tile.type]
                elif tile.tracks_owner == self.my_id or tile.tracks_owner == 2:
                    move_cost = 0
                else:
                    is_obstacle = True
                
                if is_obstacle: continue
                    
                new_cost = current_cost + move_cost
                if new_cost < cost_so_far.get((ny, nx), float('inf')):
                    cost_so_far[(ny, nx)] = new_cost
                    came_from[(ny, nx)] = (y, x)
                    heapq.heappush(pq, (new_cost, 0, ny, nx))

        if not path_found:
            return [], float('inf'), 0, 0

        path = []
        curr = (dest_y, dest_x)
        while curr:
            path.append(Coord(curr[1], curr[0]))
            curr = came_from[curr]
        path.reverse()
        
        my_expected_points = 0
        foe_expected_points = 0
        
        for coord in path[1:-1]:
            if (coord.x, coord.y) in self.town_coords_set: continue
            tile = tiles[coord.y][coord.x]
            
            owner = tile.tracks_owner
            if owner == self.my_id: my_expected_points += 1
            elif owner == (1 - self.my_id): foe_expected_points += 1
            elif owner == -1 and not tile.inked: my_expected_points += 1
                
        return path, cost_so_far[(dest_y, dest_x)], my_expected_points, foe_expected_points

    def get_all_desired_paths(self):
        all_paths = []
        for town in self.towns:
            if not town.desired_connections: continue
            for desired_town_id in town.desired_connections:
                path, cost, my_points, foe_points = self.find_shortest_path(town.id, desired_town_id)
                if path:
                    all_paths.append((town.id, desired_town_id, path, cost, my_points, foe_points))
        
        # IMPROVED SORTING FOR EARLY GAME
        def sort_key(item):
            cost = item[3]
            points = item[4]
            
            # Priority 1: Can finish immediately (Maximize points per turn NOW)
            if cost <= 3: 
                return (0, -points) 
            
            # Priority 2: Can finish in 2 turns (Early game build-up)
            # Tie-break with ROI (Points/Cost)
            if cost <= 6: 
                return (1, -points / (cost + 0.1))
                
            # Priority 3: Long term ROI
            return (2, -points / (cost + 0.1))
                
        all_paths.sort(key=sort_key)
        return all_paths

    def place_tracks_smartly(self, desired_paths: List):
        actions = []
        paint_available = 3
        built_coords = set()
        
        # Heatmap for overlaps (to use as tie-breaker for tiles)
        tile_usage = {}
        for _, _, path, _, _, _ in desired_paths[:15]:
            for coord in path:
                c_tup = (coord.x, coord.y)
                tile_usage[c_tup] = tile_usage.get(c_tup, 0) + 1

        # PATH-CENTRIC BUILDING (The "Focus Fire" Approach)
        # Instead of pooling all tiles, we process paths in order.
        # We try to fulfill Path 1 completely. If we have spare paint, we go to Path 2.
        
        for _, _, path, path_cost, my_points, foe_points in desired_paths:
            if paint_available == 0: break
            
            # Tie-breaking fix: Allow building if points are equal
            if foe_points > my_points or path_cost == 0:
                continue
            
            # Identify tiles needed for THIS path
            needed_tiles = []
            for coord in path:
                c_tuple = (coord.x, coord.y)
                if c_tuple in self.town_coords_set: continue
                if c_tuple in built_coords: continue
                
                tile = self.grid.tiles[coord.y][coord.x]
                if tile.tracks_owner == -1 and not tile.inked:
                    cost = self.type_costs[tile.type]
                    needed_tiles.append((cost, coord))
            
            if not needed_tiles: continue

            # Sort needed tiles: 
            # 1. Cost (Ascending) - Buy cheap stuff first to cover distance
            # 2. Overlap (Descending) - If costs equal, buy the one used by other paths
            needed_tiles.sort(key=lambda x: (x[0], -tile_usage.get((x[1].x, x[1].y), 0)))
            
            # Spend paint on this path
            for cost, coord in needed_tiles:
                if paint_available >= cost:
                    actions.append(f"PLACE_TRACKS {coord.x} {coord.y}")
                    paint_available -= cost
                    built_coords.add((coord.x, coord.y))
                    # Mark temporary ownership to help Phase 2 expansion logic
                    self.grid.tiles[coord.y][coord.x].tracks_owner = self.my_id
                
                if paint_available == 0: break
        
        # Phase 2: Panic Expansion (Avoid wasting paint)
        # If we still have paint, we MUST spend it, but only adjacent to our network.
        if paint_available > 0:
            # Identify network
            my_network = set()
            for y in range(self.grid.height):
                for x in range(self.grid.width):
                    if self.grid.tiles[y][x].tracks_owner == self.my_id:
                        my_network.add((x, y))
            my_network.update(self.town_coords_set)
            my_network.update(built_coords)
            
            candidates = []
            visited = set()
            
            # Scan neighbors of network
            for ox, oy in my_network:
                for dy, dx in self.directions:
                    nx, ny = ox + dx, oy + dy
                    if not (0 <= ny < self.grid.height and 0 <= nx < self.grid.width): continue
                    if (nx, ny) in visited: continue
                    if (nx, ny) in my_network: continue
                    if (nx, ny) in self.town_coords_set: continue
                    
                    visited.add((nx, ny))
                    tile = self.grid.tiles[ny][nx]
                    if tile.tracks_owner == -1 and not tile.inked:
                        cost = self.type_costs[tile.type]
                        # Priority: Cost -> Overlap
                        prio_score = tile_usage.get((nx, ny), 0)
                        candidates.append((cost, prio_score, nx, ny))
            
            # Sort by cost (cheapest), then by overlap (most useful)
            candidates.sort(key=lambda x: (x[0], -x[1]))
            
            for cost, _, nx, ny in candidates:
                if paint_available >= cost:
                    actions.append(f"PLACE_TRACKS {nx} {ny}")
                    paint_available -= cost
                    built_coords.add((nx, ny))
                if paint_available == 0: break
                
        return actions

    def get_disruption_target(self) -> int | None:
        foe_id = 1 - self.my_id
        conn_stats = {} 
        
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                t = self.grid.tiles[y][x]
                for conn in t.part_of_active_connections:
                    key = (conn.from_id, conn.to_id)
                    if key not in conn_stats: conn_stats[key] = {'my':0, 'foe':0}
                    if t.tracks_owner == self.my_id: conn_stats[key]['my'] += 1
                    elif t.tracks_owner == foe_id: conn_stats[key]['foe'] += 1
        
        foe_point_conns = {k for k, v in conn_stats.items() if v['foe'] > v['my']}
        
        best_target = None
        best_val = -1.0
        
        for rid, region in self.region_by_id.items():
            if region.inked or region.has_town: continue
            
            foe_tracks = 0
            my_tracks = 0
            foe_point_tracks = 0
            active_impact = False
            
            for c in region.coords:
                t = self.grid.tiles[c.y][c.x]
                if t.tracks_owner == foe_id:
                    foe_tracks += 1
                    for conn in t.part_of_active_connections:
                        if (conn.from_id, conn.to_id) in foe_point_conns:
                            foe_point_tracks += 1
                            active_impact = True
                            break
                elif t.tracks_owner == self.my_id:
                    my_tracks += 1

            if foe_tracks == 0: continue
            if my_tracks > foe_tracks + 2: continue
            
            mult = 1.0
            if region.instability == 1: mult = 4.0
            elif region.instability == 2: mult = 10.0
            elif region.instability == 3: mult = 20.0
            
            base_val = (foe_point_tracks * 10) + (foe_tracks * 2)
            if active_impact: base_val += 20
            
            val = base_val * mult
            if val > best_val:
                best_val = val
                best_target = rid
                
        return best_target

    def game_turn(self):
        desired_paths = self.get_all_desired_paths()
        actions = self.place_tracks_smartly(desired_paths)
        
        disrupt = self.get_disruption_target()
        if disrupt is not None:
            actions.append(f"DISRUPT {disrupt}")
            
        if actions:
            print(";".join(actions))
        else:
            print("WAIT")

def main():
    game = Game()
    game.init()
    while True:
        game.parse()
        game.game_turn()

if __name__ == "__main__":
    main()