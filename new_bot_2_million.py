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
                    
                    # Update region instability cache
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
        """
        Optimized Dijkstra with path reconstruction.
        """
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
        counter = 0
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
                
                # Cost Logic
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
                    counter += 1
                    heapq.heappush(pq, (new_cost, counter, ny, nx))

        if not path_found:
            return [], float('inf'), 0, 0

        # Reconstruct
        path = []
        curr = (dest_y, dest_x)
        while curr:
            path.append(Coord(curr[1], curr[0]))
            curr = came_from[curr]
        path.reverse()
        
        # Calc Points
        my_expected_points = 0
        foe_expected_points = 0
        
        for coord in path[1:-1]:
            tile = tiles[coord.y][coord.x]
            if (coord.x, coord.y) in self.town_coords_set: continue
            
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
        
        # IMPROVED SORTING:
        # 1. Can finish THIS turn (Cost <= 3) -> Max Points
        # 2. High ROI (Points/Cost) -> Closest to finish
        def sort_key(item):
            cost = item[3]
            points = item[4]
            
            completable = cost <= 3
            if completable:
                return (0, -points) # Group 0: Completable, descending points
            else:
                return (1, cost)    # Group 1: Others, ascending cost (closest first)
                
        all_paths.sort(key=sort_key)
        return all_paths

    def place_tracks_smartly(self, desired_paths: List):
        actions = []
        paint_available = 3
        
        buildable_tiles_dict = {}
        reinforcement_tiles_dict = {}
        tile_usage_count = {}
        
        # Keep track of active paths to limit the "mess"
        # We only care about buildables from the top N paths
        top_paths = desired_paths[:10]
        
        for _, _, path, path_cost, my_points, foe_points in top_paths:
            if foe_points >= my_points or path_cost == 0:
                continue
            
            path_coords_set = set()
            for coord in path:
                c_tuple = (coord.x, coord.y)
                if c_tuple not in self.town_coords_set:
                    path_coords_set.add(c_tuple)
                    tile_usage_count[c_tuple] = tile_usage_count.get(c_tuple, 0) + 1
            
            for coord in path:
                c_tuple = (coord.x, coord.y)
                if c_tuple in self.town_coords_set: continue

                tile = self.grid.tiles[coord.y][coord.x]
                if tile.tracks_owner == -1 and not tile.inked:
                    if c_tuple not in buildable_tiles_dict:
                        cost = self.type_costs[tile.type]
                        buildable_tiles_dict[c_tuple] = (cost, coord)
                    
                    # Reinforcement check
                    for dy, dx in self.directions:
                        ny, nx = coord.y + dy, coord.x + dx
                        if 0 <= ny < self.grid.height and 0 <= nx < self.grid.width:
                            adj_tile = self.grid.tiles[ny][nx]
                            if adj_tile.tracks_owner == self.my_id and (nx, ny) in path_coords_set:
                                if c_tuple not in reinforcement_tiles_dict:
                                    cost = self.type_costs[tile.type]
                                    region = self.region_by_id[tile.region_id]
                                    prio = (region.instability * 100) - (cost * 10) + tile_usage_count[c_tuple]
                                    reinforcement_tiles_dict[c_tuple] = (cost, coord, prio)
                                break
        
        # Construction Priority: Cost -> Overlap
        unique_buildable_tiles = [
            (coord, cost, tile_usage_count.get((coord.x, coord.y), 1)) 
            for (x, y), (cost, coord) in buildable_tiles_dict.items()
        ]
        unique_buildable_tiles.sort(key=lambda x: (x[1], -x[2]))
        
        paint_used = 0
        built_coords = set()
        
        # Phase 1: Primary Build
        for coord, cost, freq in unique_buildable_tiles:
            if paint_used + cost <= paint_available:
                actions.append(f"PLACE_TRACKS {coord.x} {coord.y}")
                paint_used += cost
                built_coords.add((coord.x, coord.y))
                self.grid.tiles[coord.y][coord.x].tracks_owner = self.my_id
            if paint_used == paint_available: break
                
        # Phase 2: Reinforcement (Safety)
        if paint_used < paint_available and reinforcement_tiles_dict:
            reinf_list = [
                (coord, cost, prio) 
                for (x, y), (cost, coord, prio) in reinforcement_tiles_dict.items()
                if (x, y) not in built_coords
            ]
            reinf_list.sort(key=lambda x: -x[2])
            
            for coord, cost, _ in reinf_list:
                if paint_used + cost <= paint_available:
                    actions.append(f"PLACE_TRACKS {coord.x} {coord.y}")
                    paint_used += cost
                    built_coords.add((coord.x, coord.y))
                if paint_used == paint_available: break
        
        # Phase 3: Clean Up (Strict Expansion)
        # Only build on tiles adjacent to tracks we own/just built.
        # This prevents "useless areas" (dots in the middle of nowhere).
        if paint_used < paint_available:
            leftovers = [
                (coord, cost) 
                for (x, y), (cost, coord) in buildable_tiles_dict.items()
                if (x, y) not in built_coords
            ]
            leftovers.sort(key=lambda x: x[1]) # Cheapest first
            
            # Identify my network
            my_network = set()
            for y in range(self.grid.height):
                for x in range(self.grid.width):
                    if self.grid.tiles[y][x].tracks_owner == self.my_id:
                        my_network.add((x, y))
            
            # Add town starts
            my_network.update(self.town_coords_set)
            # Add just built
            my_network.update(built_coords)
            
            for coord, cost in leftovers:
                if paint_used + cost <= paint_available:
                    # Check Adjacency
                    is_adj = False
                    for dy, dx in self.directions:
                        if (coord.x + dx, coord.y + dy) in my_network:
                            is_adj = True
                            break
                    
                    if is_adj:
                        actions.append(f"PLACE_TRACKS {coord.x} {coord.y}")
                        paint_used += cost
                        built_coords.add((coord.x, coord.y))
                        my_network.add((coord.x, coord.y))
                
                if paint_used == paint_available: break
                            
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