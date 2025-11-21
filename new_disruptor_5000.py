from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import sys
import math

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

    def get_region_at(self, coord: Coord) -> Region:
        return self.region_by_id[self.grid.tiles[coord.y][coord.x].region_id]

    def init(self):
        self.my_id = int(input())  # 0 or 1
        width = int(input())  # map size
        height = int(input())
        self.region_by_id = {}
        self.towns = []
        self.grid = Grid(width, height, tiles=[])

        for i in range(height):
            row: List[Tile] = []
            for j in range(width):
                # _type: 0 (PLAINS), 1 (RIVER), 2 (MOUNTAIN), 3 (POI)
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
            # desired_connections: comma-separated town ids e.g. 0,1,2,3
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

    def parse(self):
        self.my_score = int(input())
        self.foe_score = int(input())
        for i in range(self.grid.height):
            for j in range(self.grid.width):
                # instability: region inked (destroyed) when this >= 3.
                # inked: true if region is destroyed.
                # part_of_active_connections: if this cell is part of one or more railway connections, this will be town ids (separated by -) in a list separated by commas. e.g. 0-1,1-2,1-3. "x" otherwise.
                (
                    tracks_owner,
                    instability,
                    inked,
                    part_of_active_connections,
                ) = input().split()
                tracks_owner = int(tracks_owner)
                instability = int(instability)
                inked = inked != "0"
                connections: List[Connection] = []
                if part_of_active_connections == "x":
                    connections = []
                else:
                    connections = []
                    for connection in part_of_active_connections.split(","):
                        from_id, to_id = connection.split("-")
                        connections.append(Connection(int(from_id), int(to_id)))
                tile = self.grid.tiles[i][j]
                tile.tracks_owner = tracks_owner
                tile.inked = inked
                tile.instability = instability
                tile.part_of_active_connections = connections

    def find_shortest_path(self, from_town_id: int, to_town_id: int) -> tuple[List[Coord], int, int, int]:
        """
        Find shortest path between two towns.
        Returns: (path_coords, paint_cost, my_expected_points, foe_expected_points)
        """
        import heapq
        
        # Find town coordinates - use dict lookup instead of generator
        from_town = self.towns[from_town_id]
        to_town = self.towns[to_town_id]
        
        # Base cost mapping for tile types
        type_costs = {0: 1, 1: 2, 2: 3, 3: 3}  # PLAINS, RIVER, MOUNTAIN, POI
        
        # Direction priority: NORTH, EAST, SOUTH, WEST
        directions = [(-1, 0), (0, 1), (1, 0), (0, -1)]
        
        # Pre-calculate destination coordinates for faster comparison
        dest_y, dest_x = to_town.coord.y, to_town.coord.x
        
        # Dijkstra's algorithm with tie-breaking
        counter = 0
        pq = [(0, counter, from_town.coord.y, from_town.coord.x, [from_town.coord])]
        visited = set()
        
        # Pre-fetch grid tiles to avoid repeated attribute lookups
        tiles = self.grid.tiles
        height = self.grid.height
        width = self.grid.width
        foe_id = 1 - self.my_id
        
        while pq:
            cost, _, y, x, path = heapq.heappop(pq)
            
            if (y, x) in visited:
                continue
            visited.add((y, x))
            
            # Check if we reached the destination
            if y == dest_y and x == dest_x:
                # Calculate expected points if we complete this path
                my_expected_points = 0
                foe_expected_points = 0
                
                # Optimize scoring loop - skip first and last (towns)
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
            
            # Explore neighbors in priority order
            for dy, dx in directions:
                ny, nx = y + dy, x + dx
                
                # Combined bounds check and visited check
                if not (0 <= ny < height and 0 <= nx < width) or (ny, nx) in visited:
                    continue
                
                # Check if destination (avoid Coord creation)
                if ny == dest_y and nx == dest_x:
                    new_path = path + [to_town.coord]
                    counter += 1
                    heapq.heappush(pq, (cost, counter, ny, nx, new_path))
                    continue
                
                tile = tiles[ny][nx]
                
                # Skip inked tiles
                if tile.inked:
                    continue
                
                # Calculate movement cost
                move_cost = 0 if tile.tracks_owner != -1 else type_costs[tile.type]
                
                new_cost = cost + move_cost
                new_path = path + [Coord(nx, ny)]
                counter += 1
                
                heapq.heappush(pq, (new_cost, counter, ny, nx, new_path))

        # No path found
        return [], float('inf'), 0, 0


    def get_all_desired_paths(self):
        """
        Get all shortest paths for towns with desired connections.
        Returns list of (from_town_id, to_town_id, path, cost, my_points, foe_points)
        """
        all_paths = []
        
        # Pre-calculate all paths to avoid redundant calculations
        for town in self.towns:
            if not town.desired_connections:  # Skip if no desired connections
                continue
                
            for desired_town_id in town.desired_connections:
                path, cost, my_points, foe_points = self.find_shortest_path(town.id, desired_town_id)
                if path:  # Valid path found
                    all_paths.append((town.id, desired_town_id, path, cost, my_points, foe_points))
        
        # Sort by cost (cheapest first), then by my points (most points first)
        all_paths.sort(key=lambda x: (x[3], -x[4]))
        return all_paths
    

    def debug_paths(self, desired_paths: List):
        """
        Debug method to print path information including foe expected points.
        """
        if desired_paths:
            # Print the best path (first in sorted list)
            best_path = desired_paths[0]
            from_town, to_town, path, cost, my_points, foe_points = best_path
            
            print(f"Best path: Town {from_town} -> Town {to_town}", file=sys.stderr)
            print(f"Cost: {cost}, My points: {my_points}, Foe points: {foe_points}", file=sys.stderr)
            print(f"Path length: {len(path)} tiles", file=sys.stderr)
            
            # Print the path coordinates for debugging
            path_str = " -> ".join([f"({coord.x},{coord.y})" for coord in path])
            print(f"Path: {path_str}", file=sys.stderr)
            
            # Print all desired paths for analysis
            print(f"All {len(desired_paths)} desired paths:", file=sys.stderr)
            for i, (f_town, t_town, p, c, my_pts, foe_pts) in enumerate(desired_paths[:5]):  # Show top 5
                print(f"  {i+1}. Town {f_town}->{t_town}: cost={c}, my_points={my_pts}, foe_points={foe_pts}, length={len(p)}", file=sys.stderr)
        else:
            print("No desired paths found", file=sys.stderr)
    
    
    def place_tracks_smartly(self, desired_paths: List):
        """
        Smart track placement algorithm that efficiently uses all 3 paint points.
        Ignores paths where enemy has same or more expected points than us.
        Uses remaining paint to reinforce existing tracks for redundancy.
        Returns list of PLACE_TRACKS actions.
        """
        actions = []
        paint_available = 3
        type_costs = {0: 1, 1: 2, 2: 3, 3: 3}
        
        # Create a set of town coordinates for fast lookup (using tuples for speed)
        town_coords_set = {(town.coord.x, town.coord.y) for town in self.towns}
        
        # Use dict to track unique buildable tiles
        buildable_tiles_dict = {}
        reinforcement_tiles_dict = {}
        
        tiles = self.grid.tiles  # Cache grid tiles
        height = self.grid.height
        width = self.grid.width
        
        for from_town, to_town, path, path_cost, my_points, foe_points in desired_paths:
            # Skip paths where enemy has same or more expected points
            if foe_points >= my_points or path_cost == 0:
                continue
            
            # Track all tiles in this path for reinforcement consideration
            path_tiles = set()
            for coord in path:
                coord_tuple = (coord.x, coord.y)
                if coord_tuple not in town_coords_set:
                    path_tiles.add(coord_tuple)
            
            # Find buildable tiles and reinforcement opportunities
            for coord in path:
                coord_tuple = (coord.x, coord.y)
                
                # Skip towns
                if coord_tuple in town_coords_set:
                    continue

                tile = tiles[coord.y][coord.x]
                
                # Primary targets: empty tiles we can build on
                if tile.tracks_owner == -1 and not tile.inked:
                    if coord_tuple not in buildable_tiles_dict:
                        cost = type_costs[tile.type]
                        buildable_tiles_dict[coord_tuple] = (cost, coord, from_town, to_town)
                    
                    # Also check for reinforcement opportunities (adjacent to our tracks)
                    # Check if any adjacent tile has our tracks
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = coord.y + dy, coord.x + dx
                        if 0 <= ny < height and 0 <= nx < width:
                            adj_tile = tiles[ny][nx]
                            if adj_tile.tracks_owner == self.my_id and (nx, ny) in path_tiles:
                                if coord_tuple not in reinforcement_tiles_dict:
                                    cost = type_costs[tile.type]
                                    region = self.region_by_id[tile.region_id]
                                    # Priority: prefer vulnerable regions (high instability) and cheaper tiles
                                    priority = region.instability * 10 - cost
                                    reinforcement_tiles_dict[coord_tuple] = (cost, coord, from_town, to_town, priority)
                                break
        
        # Convert to sorted list (sort by cost for primary targets)
        unique_buildable_tiles = [(coord, cost, from_town, to_town) 
                                  for (x, y), (cost, coord, from_town, to_town) 
                                  in buildable_tiles_dict.items()]
        unique_buildable_tiles.sort(key=lambda x: x[1])
        
        paint_used = 0
        built_coords = set()  # Track what we've built this turn
        
        # Phase 1: Build new tracks on the actual path (primary objective)
        for coord, track_cost, from_town, to_town in unique_buildable_tiles:
            if paint_used + track_cost <= paint_available:
                actions.append(f"PLACE_TRACKS {coord.x} {coord.y}")
                paint_used += track_cost
                built_coords.add((coord.x, coord.y))
                print(f"Building new track at ({coord.x},{coord.y}): cost={track_cost} (path {from_town}->{to_town})", file=sys.stderr)
                
                # Mark this tile as owned (for this turn's logic only)
                tiles[coord.y][coord.x].tracks_owner = self.my_id
            
            if paint_used == paint_available:
                break
        
        # Phase 2: Use remaining paint to build redundant paths
        if paint_used < paint_available and reinforcement_tiles_dict:
            print(f"Building redundant tracks with {paint_available - paint_used} remaining paint", file=sys.stderr)
            
            # Sort reinforcement targets by priority (high instability regions first, then cheaper)
            reinforcement_tiles = [(coord, cost, from_town, to_town, priority) 
                                   for (x, y), (cost, coord, from_town, to_town, priority) 
                                   in reinforcement_tiles_dict.items()
                                   if (x, y) not in built_coords]  # Skip already built
            reinforcement_tiles.sort(key=lambda x: -x[4])  # Higher priority first
            
            for coord, track_cost, from_town, to_town, priority in reinforcement_tiles:
                if paint_used + track_cost <= paint_available:
                    actions.append(f"PLACE_TRACKS {coord.x} {coord.y}")
                    paint_used += track_cost
                    built_coords.add((coord.x, coord.y))
                    region = self.region_by_id[tiles[coord.y][coord.x].region_id]
                    print(f"Building redundant track at ({coord.x},{coord.y}): cost={track_cost}, region instability={region.instability}", file=sys.stderr)
                
                if paint_used == paint_available:
                    break
        
        # Phase 3: If still have paint, build on ANY cheap available tiles from any path
        if paint_used < paint_available:
            print(f"Using {paint_available - paint_used} remaining paint on any available tiles from paths", file=sys.stderr)
            
            # Collect all empty tiles not yet built, sorted by cost
            all_empty_tiles = []
            for coord_tuple, (cost, coord, from_town, to_town) in buildable_tiles_dict.items():
                if coord_tuple not in built_coords:
                    all_empty_tiles.append((coord, cost))
            
            all_empty_tiles.sort(key=lambda x: x[1])  # Cheapest first
            
            for coord, track_cost in all_empty_tiles:
                if paint_used + track_cost <= paint_available:
                    actions.append(f"PLACE_TRACKS {coord.x} {coord.y}")
                    paint_used += track_cost
                    built_coords.add((coord.x, coord.y))
                    print(f"Using leftover paint at ({coord.x},{coord.y}): cost={track_cost}", file=sys.stderr)
                
                if paint_used == paint_available:
                    break
        
        # Phase 4: LAST RESORT - scan entire map for ANY buildable tile
        if paint_used < paint_available:
            print(f"Scanning entire map for {paint_available - paint_used} remaining paint", file=sys.stderr)
            
            # Collect all empty tiles on the entire map
            map_empty_tiles = []
            for y in range(height):
                for x in range(width):
                    coord_tuple = (x, y)
                    
                    # Skip if already built, is a town, or unavailable
                    if coord_tuple in built_coords or coord_tuple in town_coords_set:
                        continue
                    
                    tile = tiles[y][x]
                    if tile.tracks_owner == -1 and not tile.inked:
                        cost = type_costs[tile.type]
                        coord = Coord(x, y)
                        map_empty_tiles.append((coord, cost))
            
            # Sort by cost (cheapest first)
            map_empty_tiles.sort(key=lambda x: x[1])
            
            for coord, track_cost in map_empty_tiles:
                if paint_used + track_cost <= paint_available:
                    actions.append(f"PLACE_TRACKS {coord.x} {coord.y}")
                    paint_used += track_cost
                    print(f"Last resort: building at ({coord.x},{coord.y}): cost={track_cost}", file=sys.stderr)
                
                if paint_used == paint_available:
                    break
        
        print(f"Total: {len(actions)} tracks placed using {paint_used}/3 paint", file=sys.stderr)
        
        if paint_used < paint_available:
            print(f"Warning: {paint_available - paint_used} paint points unused (truly no valid targets on entire map!)", file=sys.stderr)
        
        return actions


    def get_disruption_target(self) -> int | None:
        """Choose the best region to disrupt with urgency for almost-inked regions."""
        foe_id = 1 - self.my_id
        
        # Build connection statistics (same as before)
        active_connections = set()
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                tile = self.grid.tiles[y][x]
                for conn in tile.part_of_active_connections:
                    active_connections.add((conn.from_id, conn.to_id))
        
        connection_stats = {}
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                tile = self.grid.tiles[y][x]
                for conn in tile.part_of_active_connections:
                    conn_key = (conn.from_id, conn.to_id)
                    if conn_key not in connection_stats:
                        connection_stats[conn_key] = {'my': 0, 'foe': 0, 'total': 0}
                    
                    connection_stats[conn_key]['total'] += 1
                    if tile.tracks_owner == self.my_id:
                        connection_stats[conn_key]['my'] += 1
                    elif tile.tracks_owner == foe_id:
                        connection_stats[conn_key]['foe'] += 1
        
        foe_point_connections = set()
        for conn_key, stats in connection_stats.items():
            if stats['foe'] > stats['my']:
                foe_point_connections.add(conn_key)
        
        # UNIFIED candidate list
        all_candidates = []
        
        for region_id, region in self.region_by_id.items():
            if region.inked or region.has_town:
                continue
            
            # Collect region data
            affected_point_connections = set()
            affected_my_connections = set()
            foe_tracks_in_region = 0
            my_tracks_in_region = 0
            foe_point_tracks_in_region = 0
            
            for coord in region.coords:
                tile = self.grid.tiles[coord.y][coord.x]
                
                if tile.tracks_owner == foe_id:
                    foe_tracks_in_region += 1
                    for conn in tile.part_of_active_connections:
                        conn_key = (conn.from_id, conn.to_id)
                        if conn_key in foe_point_connections:
                            foe_point_tracks_in_region += 1
                            affected_point_connections.add(conn_key)
                            break
                
                elif tile.tracks_owner == self.my_id:
                    my_tracks_in_region += 1
                    for conn in tile.part_of_active_connections:
                        conn_key = (conn.from_id, conn.to_id)
                        if conn_key in connection_stats and connection_stats[conn_key]['my'] > connection_stats[conn_key]['foe']:
                            affected_my_connections.add(conn_key)
                            break
            
            # Skip if no enemy presence
            if foe_tracks_in_region == 0:
                continue
            
            # Skip if we'd lose too many of our own tracks
            if my_tracks_in_region > foe_tracks_in_region + 2:
                continue
            
            disruptions_to_ink = 3 - region.instability
            
            # URGENCY MULTIPLIER: Massively boost almost-inked regions
            urgency_multiplier = {
                2: 10.0,   # 1 disruption away = 10x multiplier
                1: 4.0,    # 2 disruptions away = 4x multiplier
                0: 1.0     # Fresh region = no bonus
            }[region.instability]
            
            # Calculate base strategic value
            if affected_point_connections:
                foe_points_lost = sum(connection_stats[ck]['foe'] for ck in affected_point_connections if ck in connection_stats)
                my_points_lost = sum(connection_stats[ck]['my'] for ck in affected_my_connections if ck in connection_stats)
                net_point_benefit = foe_points_lost - my_points_lost
                
                base_value = (
                    foe_point_tracks_in_region * 10 +
                    net_point_benefit * 8 +
                    len(affected_point_connections) * 6 +
                    foe_tracks_in_region * 2
                )
                tier = 1
            else:
                # Non-point-generating regions (early game)
                base_value = (
                    foe_tracks_in_region * 5 -
                    my_tracks_in_region * 3
                )
                tier = 2
            
            # Apply urgency multiplier to final value
            final_value = base_value * urgency_multiplier
            
            all_candidates.append({
                'region_id': region_id,
                'value': final_value,
                'base_value': base_value,
                'urgency_mult': urgency_multiplier,
                'foe_tracks': foe_tracks_in_region,
                'my_tracks': my_tracks_in_region,
                'instability': region.instability,
                'tier': tier
            })
        
        if not all_candidates:
            print("No disruption targets found", file=sys.stderr)
            return None
        
        # Sort by final value (which includes urgency)
        all_candidates.sort(key=lambda x: x['value'], reverse=True)
        best = all_candidates[0]
        
        print(f"[TIER {best['tier']}] Disrupt: R{best['region_id']} "
              f"value={best['value']:.1f} (base={best['base_value']:.1f} × {best['urgency_mult']}x) "
              f"foe={best['foe_tracks']} my={best['my_tracks']} inst={best['instability']}", 
              file=sys.stderr)
        
        return best['region_id']
        

    def game_turn(self):
        # Get all desired paths sorted by cost, then by points
        desired_paths = self.get_all_desired_paths()
        
        # Debug path information
        self.debug_paths(desired_paths)
        
        # Use smart track placement algorithm
        actions = self.place_tracks_smartly(desired_paths)
        
        # Add disruption action
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