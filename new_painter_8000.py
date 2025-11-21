from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Set
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

# Connect towns with your train tracks and disrupt the opponent's.
class Game:
    my_id: int
    grid: Grid
    towns: List[Town]
    region_by_id: Dict[int, Region]
    my_score: int
    foe_score: int
    
    # Cache these for performance
    _town_coords_set: Set[Tuple[int, int]]
    _type_costs: Tuple[int, int, int, int]
    _directions: Tuple[Tuple[int, int], ...]

    def get_region_at(self, coord: Coord) -> Region:
        return self.region_by_id[self.grid.tiles[coord.y][coord.x].region_id]

    def init(self):
        self.my_id = int(input())  # 0 or 1
        width = int(input())  # map size
        height = int(input())
        self.region_by_id = {}
        self.towns = []
        self.grid = Grid(width, height, tiles=[])
        
        # Cache constants
        self._type_costs = (1, 2, 3, 3)
        self._directions = ((-1, 0), (0, 1), (1, 0), (0, -1))

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
                coord = Coord(x=j, y=i)
                region.coords.append(coord)
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
        
        # Cache town coordinates
        self._town_coords_set = {(town.coord.x, town.coord.y) for town in self.towns}

    def parse(self):
        self.my_score = int(input())
        self.foe_score = int(input())
        
        tiles = self.grid.tiles
        for i in range(self.grid.height):
            for j in range(self.grid.width):
                tracks_owner, instability, inked, part_of_active_connections = input().split()
                
                tile = tiles[i][j]
                tile.tracks_owner = int(tracks_owner)
                tile.instability = int(instability)
                tile.inked = inked != "0"
                
                if part_of_active_connections == "x":
                    tile.part_of_active_connections = []
                else:
                    connections = []
                    for connection in part_of_active_connections.split(","):
                        from_id, to_id = connection.split("-")
                        connections.append(Connection(int(from_id), int(to_id)))
                    tile.part_of_active_connections = connections

    def find_shortest_path(self, from_town_id: int, to_town_id: int) -> Tuple[List[Coord], int, int, int]:
        """Find shortest path between two towns."""
        from_town = self.towns[from_town_id]
        to_town = self.towns[to_town_id]
        
        dest_y, dest_x = to_town.coord.y, to_town.coord.x
        tiles = self.grid.tiles
        height = self.grid.height
        width = self.grid.width
        foe_id = 1 - self.my_id
        type_costs = self._type_costs
        directions = self._directions
        
        counter = 0
        pq = [(0, counter, from_town.coord.y, from_town.coord.x, [from_town.coord])]
        visited = set()
        
        while pq:
            cost, _, y, x, path = heapq.heappop(pq)
            
            if (y, x) in visited:
                continue
            visited.add((y, x))
            
            if y == dest_y and x == dest_x:
                my_expected_points = 0
                foe_expected_points = 0
                
                for coord in path[1:-1]:
                    tile = tiles[coord.y][coord.x]
                    owner = tile.tracks_owner
                    
                    if owner == self.my_id:
                        my_expected_points += 1
                    elif owner == foe_id:
                        foe_expected_points += 1
                    elif owner == -1 and not tile.inked:
                        my_expected_points += 1
                
                return path, cost, my_expected_points, foe_expected_points
            
            for dy, dx in directions:
                ny, nx = y + dy, x + dx
                
                if not (0 <= ny < height and 0 <= nx < width) or (ny, nx) in visited:
                    continue
                
                if ny == dest_y and nx == dest_x:
                    new_path = path + [to_town.coord]
                    counter += 1
                    heapq.heappush(pq, (cost, counter, ny, nx, new_path))
                    continue
                
                tile = tiles[ny][nx]
                
                if tile.inked:
                    continue
                
                move_cost = 0 if tile.tracks_owner != -1 else type_costs[tile.type]
                new_cost = cost + move_cost
                new_path = path + [Coord(nx, ny)]
                counter += 1
                
                heapq.heappush(pq, (new_cost, counter, ny, nx, new_path))

        return [], float('inf'), 0, 0


    def get_all_desired_paths(self):
        """Get all shortest paths for towns with desired connections."""
        all_paths = []
        
        for town in self.towns:
            if not town.desired_connections:
                continue
                
            for desired_town_id in town.desired_connections:
                path, cost, my_points, foe_points = self.find_shortest_path(town.id, desired_town_id)
                if path:
                    all_paths.append((town.id, desired_town_id, path, cost, my_points, foe_points))
        
        all_paths.sort(key=lambda x: (x[3], -x[4]))
        return all_paths
    

    def debug_paths(self, desired_paths: List):
        """Minimal debug output."""
        if desired_paths:
            best_path = desired_paths[0]
            from_town, to_town, path, cost, my_points, foe_points = best_path
            print(f"Best: T{from_town}->T{to_town} c={cost} my={my_points} foe={foe_points} len={len(path)}", file=sys.stderr)
        else:
            print("No paths", file=sys.stderr)
    
    
    def place_tracks_smartly(self, desired_paths: List):
        """Smart track placement prioritizing connection completion and stability."""
        actions = []
        paint_available = 3
        
        town_coords_set = self._town_coords_set
        type_costs = self._type_costs
        tiles = self.grid.tiles
        height = self.grid.height
        width = self.grid.width
        foe_id = 1 - self.my_id
        
        # Analyze each path for completion potential
        path_priorities = []
        
        for from_town, to_town, path, path_cost, my_points, foe_points in desired_paths:
            if foe_points >= my_points:
                continue
            
            # Count what's needed to complete this path
            needed_tiles = []
            total_needed_cost = 0
            completion_blocked = False
            has_unstable = False
            
            for coord in path:
                if (coord.x, coord.y) in town_coords_set:
                    continue
                
                tile = tiles[coord.y][coord.x]
                
                if tile.inked:
                    completion_blocked = True
                    break
                
                if tile.tracks_owner == -1:
                    cost = type_costs[tile.type]
                    total_needed_cost += cost
                    region = self.region_by_id[tile.region_id]
                    if region.instability > 0:
                        has_unstable = True
                    needed_tiles.append((coord, cost, region.instability))
            
            if completion_blocked or total_needed_cost == 0:
                continue
            
            # Calculate priority score
            can_complete = total_needed_cost <= paint_available
            points_gain = my_points - foe_points
            
            # High priority: completable paths that give points
            if can_complete:
                priority = 1000 + points_gain * 100 - total_needed_cost
            else:
                # Partial completion: favor paths close to completion
                priority = 500 + points_gain * 50 - total_needed_cost
            
            # Penalty for unstable regions
            if has_unstable:
                priority -= 200
            
            path_priorities.append({
                'from_town': from_town,
                'to_town': to_town,
                'needed_tiles': needed_tiles,
                'total_cost': total_needed_cost,
                'priority': priority,
                'can_complete': can_complete,
                'points_gain': points_gain
            })
        
        # Sort by priority
        path_priorities.sort(key=lambda x: -x['priority'])
        
        paint_used = 0
        built_coords = set()
        
        # Phase 1: Complete high-priority paths
        for path_info in path_priorities:
            if not path_info['can_complete'] or paint_used + path_info['total_cost'] > paint_available:
                continue
            
            for coord, cost, instability in path_info['needed_tiles']:
                coord_tuple = (coord.x, coord.y)
                if coord_tuple in built_coords:
                    continue
                
                actions.append(f"PLACE_TRACKS {coord.x} {coord.y}")
                paint_used += cost
                built_coords.add(coord_tuple)
                tiles[coord.y][coord.x].tracks_owner = self.my_id
            
            print(f"Completed T{path_info['from_town']}->T{path_info['to_town']} (+{path_info['points_gain']}pts)", file=sys.stderr)
        
        # Phase 2: Partial progress on high-value paths
        if paint_used < paint_available:
            for path_info in path_priorities:
                if path_info['can_complete']:
                    continue
                
                for coord, cost, instability in path_info['needed_tiles']:
                    if paint_used + cost > paint_available:
                        continue
                    
                    coord_tuple = (coord.x, coord.y)
                    if coord_tuple in built_coords:
                        continue
                    
                    # Skip unstable regions unless critical
                    if instability > 0 and path_info['priority'] < 600:
                        continue
                    
                    actions.append(f"PLACE_TRACKS {coord.x} {coord.y}")
                    paint_used += cost
                    built_coords.add(coord_tuple)
                    tiles[coord.y][coord.x].tracks_owner = self.my_id
                    
                    if paint_used >= paint_available:
                        break
                
                if paint_used >= paint_available:
                    break
        
        # Phase 3: Reinforce threatened connections
        if paint_used < paint_available:
            threatened_tiles = []
            
            for y in range(height):
                for x in range(width):
                    tile = tiles[y][x]
                    if tile.tracks_owner != self.my_id or not tile.part_of_active_connections:
                        continue
                    
                    region = self.region_by_id[tile.region_id]
                    if region.instability == 0 or region.inked:
                        continue
                    
                    # Find adjacent buildable tiles in same region
                    for dy, dx in self._directions:
                        ny, nx = y + dy, x + dx
                        if not (0 <= ny < height and 0 <= nx < width):
                            continue
                        
                        adj_tile = tiles[ny][nx]
                        coord_tuple = (nx, ny)
                        
                        if (coord_tuple not in built_coords and 
                            coord_tuple not in town_coords_set and
                            adj_tile.region_id == tile.region_id and
                            adj_tile.tracks_owner == -1 and 
                            not adj_tile.inked):
                            
                            cost = type_costs[adj_tile.type]
                            priority = region.instability * 100
                            threatened_tiles.append((nx, ny, cost, priority))
            
            threatened_tiles.sort(key=lambda x: -x[3])
            
            for x, y, cost, priority in threatened_tiles:
                if paint_used + cost > paint_available:
                    continue
                
                actions.append(f"PLACE_TRACKS {x} {y}")
                paint_used += cost
                built_coords.add((x, y))
                
                if paint_used >= paint_available:
                    break
        
        # Phase 4: Use remaining paint on cheapest tiles from paths
        if paint_used < paint_available:
            cheap_tiles = []
            for path_info in path_priorities:
                for coord, cost, instability in path_info['needed_tiles']:
                    coord_tuple = (coord.x, coord.y)
                    if coord_tuple not in built_coords and instability == 0:
                        cheap_tiles.append((coord.x, coord.y, cost))
            
            cheap_tiles.sort(key=lambda x: x[2])
            
            for x, y, cost in cheap_tiles:
                if paint_used + cost > paint_available:
                    continue
                
                actions.append(f"PLACE_TRACKS {x} {y}")
                paint_used += cost
                built_coords.add((x, y))
                
                if paint_used >= paint_available:
                    break
        
        print(f"Placed {len(actions)} tracks ({paint_used}/3 paint)", file=sys.stderr)
        return actions


    def get_disruption_target(self) -> int | None:
        """Choose best region to disrupt with urgency multiplier."""
        foe_id = 1 - self.my_id
        tiles = self.grid.tiles
        height = self.grid.height
        width = self.grid.width
        
        # Build connection stats efficiently using list [my, foe]
        connection_stats = {}
        
        for y in range(height):
            row = tiles[y]
            for x in range(width):
                tile = row[x]
                owner = tile.tracks_owner
                
                for conn in tile.part_of_active_connections:
                    conn_key = (conn.from_id, conn.to_id)
                    
                    if conn_key not in connection_stats:
                        connection_stats[conn_key] = [0, 0]  # [my, foe]
                    
                    if owner == self.my_id:
                        connection_stats[conn_key][0] += 1
                    elif owner == foe_id:
                        connection_stats[conn_key][1] += 1
        
        # Identify foe point connections
        foe_point_connections = {k for k, v in connection_stats.items() if v[1] > v[0]}
        
        # Track best candidate inline (avoid list allocation)
        best_region_id = None
        best_value = -1
        best_tier = 0
        
        for region_id, region in self.region_by_id.items():
            if region.inked or region.has_town:
                continue
            
            foe_tracks = 0
            my_tracks = 0
            foe_point_tracks = 0
            affected_point_conns = set()
            affected_my_conns = set()
            
            for coord in region.coords:
                tile = tiles[coord.y][coord.x]
                owner = tile.tracks_owner
                
                if owner == foe_id:
                    foe_tracks += 1
                    for conn in tile.part_of_active_connections:
                        conn_key = (conn.from_id, conn.to_id)
                        if conn_key in foe_point_connections:
                            foe_point_tracks += 1
                            affected_point_conns.add(conn_key)
                            break
                
                elif owner == self.my_id:
                    my_tracks += 1
                    for conn in tile.part_of_active_connections:
                        conn_key = (conn.from_id, conn.to_id)
                        if conn_key in connection_stats and connection_stats[conn_key][0] > connection_stats[conn_key][1]:
                            affected_my_conns.add(conn_key)
                            break
            
            if foe_tracks == 0 or my_tracks > foe_tracks + 2:
                continue
            
            # Urgency multiplier based on instability
            urgency = 10.0 if region.instability == 2 else (4.0 if region.instability == 1 else 1.0)
            
            # Calculate value
            if affected_point_conns:
                foe_pts_lost = sum(connection_stats[ck][1] for ck in affected_point_conns)
                my_pts_lost = sum(connection_stats[ck][0] for ck in affected_my_conns)
                
                base_value = (
                    foe_point_tracks * 10 +
                    (foe_pts_lost - my_pts_lost) * 8 +
                    len(affected_point_conns) * 6 +
                    foe_tracks * 2
                )
                tier = 1
            else:
                base_value = foe_tracks * 5 - my_tracks * 3
                tier = 2
            
            final_value = base_value * urgency
            
            if final_value > best_value:
                best_value = final_value
                best_region_id = region_id
                best_tier = tier
        
        if best_region_id:
            print(f"[T{best_tier}] Disrupt R{best_region_id}: {best_value:.0f}", file=sys.stderr)
        
        return best_region_id
        

    def game_turn(self):
        desired_paths = self.get_all_desired_paths()
        self.debug_paths(desired_paths)
        
        actions = self.place_tracks_smartly(desired_paths)
        
        disruption_target = self.get_disruption_target()
        if disruption_target is not None:
            actions.append(f"DISRUPT {disruption_target}")
        
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


main()