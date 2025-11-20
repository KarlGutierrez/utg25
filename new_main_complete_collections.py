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
        
        # Find town coordinates
        from_town = next(t for t in self.towns if t.id == from_town_id)
        to_town = next(t for t in self.towns if t.id == to_town_id)
        
        # Base cost mapping for tile types
        type_costs = {0: 1, 1: 2, 2: 3, 3: 3}  # PLAINS, RIVER, MOUNTAIN, POI
        
        # Direction priority: NORTH, EAST, SOUTH, WEST
        directions = [(-1, 0), (0, 1), (1, 0), (0, -1)]
        
        # Dijkstra's algorithm with tie-breaking
        # State: (cost, counter, y, x, path) - added counter to avoid comparing paths
        counter = 0
        pq = [(0, counter, from_town.coord.y, from_town.coord.x, [from_town.coord])]
        visited = set()
        
        while pq:
            cost, _, y, x, path = heapq.heappop(pq)
            
            if (y, x) in visited:
                continue
            visited.add((y, x))
            
            # Check if we reached the destination
            if y == to_town.coord.y and x == to_town.coord.x:
                # Calculate expected points if we complete this path
                my_expected_points = 0
                foe_expected_points = 0
                foe_id = 1 - self.my_id
                
                for coord in path:
                    if coord == from_town.coord or coord == to_town.coord:
                        continue  # Towns don't count for scoring
                        
                    tile = self.grid.tiles[coord.y][coord.x]
                    
                    # If we already own this track, we get points
                    if tile.tracks_owner == self.my_id:
                        my_expected_points += 1
                    # If opponent owns this track, they get points
                    elif tile.tracks_owner == foe_id:
                        foe_expected_points += 1
                    # If no one owns this track and it's not inked, we'll build it and get points
                    elif tile.tracks_owner == -1 and not tile.inked:
                        my_expected_points += 1
                    # If it's a neutral track (owner = 2), nobody gets points
                    elif tile.tracks_owner == 2:
                        my_expected_points += 0
                        foe_expected_points += 0
                
                return path, cost, my_expected_points, foe_expected_points
            
            # Explore neighbors in priority order (NORTH, EAST, SOUTH, WEST)
            for dy, dx in directions:
                ny, nx = y + dy, x + dx
                
                # Check bounds
                if not (0 <= ny < self.grid.height and 0 <= nx < self.grid.width):
                    continue
                
                if (ny, nx) in visited:
                    continue
                
                coord = Coord(nx, ny)
                
                # If this is the destination town, no additional cost
                if coord == to_town.coord:
                    new_path = path + [coord]
                    counter += 1
                    heapq.heappush(pq, (cost, counter, ny, nx, new_path))
                    continue
                
                tile = self.grid.tiles[ny][nx]
                
                # Skip inked (destroyed) tiles
                if tile.inked:
                    continue
                
                # Calculate movement cost based on existing tracks
                if tile.tracks_owner != -1:  # Track already exists
                    move_cost = 0  # No cost to use existing track
                else:
                    move_cost = type_costs[tile.type]  # Cost to build new track
                
                new_cost = cost + move_cost
                new_path = path + [coord]
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
        
        for town in self.towns:
            for desired_town_id in town.desired_connections:
                path, cost, my_points, foe_points = self.find_shortest_path(town.id, desired_town_id)
                if path:  # Valid path found
                    all_paths.append((town.id, desired_town_id, path, cost, my_points, foe_points))
        
        # Sort by cost (cheapest first), then by my points (most points first when cost is equal)
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
        Prioritizes completing connections before starting new ones.
        Ignores paths where enemy has same or more expected points than us.
        Returns list of PLACE_TRACKS actions.
        """
        actions = []
        paint_available = 3
        type_costs = {0: 1, 1: 2, 2: 3, 3: 3}  # PLAINS, RIVER, MOUNTAIN, POI

        # Create a set of town coordinates for fast lookup
        town_coords = {town.coord for town in self.towns}
        
        # Collect buildable tiles grouped by connection
        # Key: (from_town, to_town), Value: list of (coord, cost)
        tiles_by_connection = {}
        
        for from_town, to_town, path, path_cost, my_points, foe_points in desired_paths:
            # Skip paths where enemy has same or more expected points
            if foe_points >= my_points:
                print(f"Skipping path {from_town}->{to_town}: foe_points={foe_points} >= my_points={my_points}", file=sys.stderr)
                continue
                
            if path_cost == 0:  # Path already complete
                continue
            
            connection_key = (from_town, to_town)
            buildable_tiles = []
            
            # Find buildable tiles in this path
            for coord in path:
                # Skip towns
                if coord in town_coords:
                    continue

                tile = self.grid.tiles[coord.y][coord.x]
                if tile.tracks_owner == -1 and not tile.inked:  # Can build here
                    cost = type_costs[tile.type]
                    buildable_tiles.append((coord, cost))
            
            if buildable_tiles:
                tiles_by_connection[connection_key] = {
                    'tiles': buildable_tiles,
                    'remaining_cost': path_cost,
                    'my_points': my_points,
                    'foe_points': foe_points
                }
        
        # Sort connections by remaining cost (prioritize nearly complete connections)
        sorted_connections = sorted(
            tiles_by_connection.items(),
            key=lambda x: (x[1]['remaining_cost'], -x[1]['my_points'])
        )
        
        print(f"Found {len(sorted_connections)} connections to build:", file=sys.stderr)
        for (from_town, to_town), info in sorted_connections[:5]:
            print(f"  {from_town}->{to_town}: remaining_cost={info['remaining_cost']}, tiles={len(info['tiles'])}, points={info['my_points']}", file=sys.stderr)
        
        paint_used = 0
        built_coords = set()
        
        # Build tiles connection by connection, prioritizing cheaper/nearly complete ones
        for (from_town, to_town), info in sorted_connections:
            # Sort tiles within this connection by cost (cheapest first)
            tiles = sorted(info['tiles'], key=lambda x: x[1])
            
            connection_built_any = False
            for coord, track_cost in tiles:
                # Skip if already built this turn
                if coord in built_coords:
                    continue
                
                if paint_used + track_cost <= paint_available:
                    actions.append(f"PLACE_TRACKS {coord.x} {coord.y}")
                    paint_used += track_cost
                    built_coords.add(coord)
                    connection_built_any = True
                    print(f"Placing track at ({coord.x},{coord.y}): cost={track_cost} (for path {from_town}->{to_town})", file=sys.stderr)
                    
                    # Mark this tile as owned to avoid building on it again in this turn
                    tile = self.grid.tiles[coord.y][coord.x]
                    tile.tracks_owner = self.my_id
                else:
                    # If we can't afford this tile in this connection, try next connection
                    # (might have cheaper tiles)
                    break
            
            # If we used paint for this connection and have paint left, continue to next connection
            # If we're out of paint, stop
            if paint_used >= paint_available:
                break
        
        print(f"Built {len(actions)} tracks using {paint_used}/3 paint", file=sys.stderr)
        
        if paint_used < paint_available and len(sorted_connections) > 0:
            print(f"Warning: {paint_available - paint_used} paint points unused!", file=sys.stderr)
        
        return actions


    def get_disruption_target(self) -> int | None:
        """
        Optimized disruption targeting that finds the most valuable region to disrupt.
        Returns region_id to disrupt, or None if no good target.
        """
        foe_id = 1 - self.my_id
        
        # Build connection track counts in a single grid pass
        connection_tracks = {}  # {(from_id, to_id): {'my': count, 'foe': count}}
        
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                tile = self.grid.tiles[y][x]
                
                for conn in tile.part_of_active_connections:
                    conn_key = (conn.from_id, conn.to_id)
                    
                    if conn_key not in connection_tracks:
                        connection_tracks[conn_key] = {'my': 0, 'foe': 0}
                    
                    if tile.tracks_owner == self.my_id:
                        connection_tracks[conn_key]['my'] += 1
                    elif tile.tracks_owner == foe_id:
                        connection_tracks[conn_key]['foe'] += 1
        
        disruption_candidates = []
        
        # Analyze each region
        for region_id, region in self.region_by_id.items():
            # Quick filters
            if region.inked or region.has_town:
                continue
            
            # Collect region data in one pass
            affected_connections = set()
            foe_tracks_in_region = 0
            my_tracks_in_region = 0
            
            for coord in region.coords:
                tile = self.grid.tiles[coord.y][coord.x]
                
                # Collect affected connections
                for conn in tile.part_of_active_connections:
                    affected_connections.add((conn.from_id, conn.to_id))
                
                # Count tracks
                if tile.tracks_owner == foe_id:
                    foe_tracks_in_region += 1
                elif tile.tracks_owner == self.my_id:
                    my_tracks_in_region += 1
            
            # Quick filters
            if not affected_connections or my_tracks_in_region > 0 or foe_tracks_in_region == 0:
                continue
            
            # Calculate total tracks from pre-computed connection_tracks
            my_total_tracks_in_connections = 0
            foe_total_tracks_in_connections = 0
            
            for conn_key in affected_connections:
                if conn_key in connection_tracks:
                    my_total_tracks_in_connections += connection_tracks[conn_key]['my']
                    foe_total_tracks_in_connections += connection_tracks[conn_key]['foe']
            
            # Skip if we have more tracks in affected connections
            if my_total_tracks_in_connections > foe_total_tracks_in_connections:
                continue
            
            # Calculate disruption value
            disruptions_to_ink = 3 - region.instability
            net_connection_benefit = foe_total_tracks_in_connections - my_total_tracks_in_connections
            
            value = (foe_tracks_in_region * 2 + 
                    len(affected_connections) * 2 + 
                    net_connection_benefit * 3 +
                    (3 - disruptions_to_ink) * 3)
            
            disruption_candidates.append({
                'region_id': region_id,
                'value': value,
                'foe_tracks_in_region': foe_tracks_in_region,
                'affected_connections': len(affected_connections),
                'my_total_tracks': my_total_tracks_in_connections,
                'foe_total_tracks': foe_total_tracks_in_connections,
                'instability': region.instability,
                'disruptions_needed': disruptions_to_ink
            })
        
        # Return best candidate
        if disruption_candidates:
            disruption_candidates.sort(key=lambda x: x['value'], reverse=True)
            best = disruption_candidates[0]
            
            print(f"Disruption target: Region {best['region_id']}", file=sys.stderr)
            print(f"  Value={best['value']}, Foe tracks in region={best['foe_tracks_in_region']}", file=sys.stderr)
            print(f"  Affected connections={best['affected_connections']}", file=sys.stderr)
            print(f"  Total: Foe tracks={best['foe_total_tracks']}, My tracks={best['my_total_tracks']}", file=sys.stderr)
            
            return best['region_id']
        else:
            print("No disruption targets found", file=sys.stderr)
            return None
        

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