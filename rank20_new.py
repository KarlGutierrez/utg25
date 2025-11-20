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
        Returns list of PLACE_TRACKS actions.
        """
        actions = []
        paint_available = 3
        type_costs = {0: 1, 1: 2, 2: 3, 3: 3}
        
        # Create a set of town coordinates for fast lookup (using tuples for speed)
        town_coords_set = {(town.coord.x, town.coord.y) for town in self.towns}
        
        # Use dict to track unique buildable tiles (faster than list + set)
        # Key: (x, y), Value: (cost, from_town, to_town)
        buildable_tiles_dict = {}
        
        tiles = self.grid.tiles  # Cache grid tiles
        
        for from_town, to_town, path, path_cost, my_points, foe_points in desired_paths:
            # Skip paths where enemy has same or more expected points
            if foe_points >= my_points or path_cost == 0:
                continue
            
            # Find buildable tiles in this path
            for coord in path:
                coord_tuple = (coord.x, coord.y)
                
                # Skip towns and already processed coords
                if coord_tuple in town_coords_set or coord_tuple in buildable_tiles_dict:
                    continue

                tile = tiles[coord.y][coord.x]
                if tile.tracks_owner == -1 and not tile.inked:
                    cost = type_costs[tile.type]
                    buildable_tiles_dict[coord_tuple] = (cost, coord, from_town, to_town)
        
        # Convert to sorted list (sort once instead of multiple times)
        unique_buildable_tiles = [(coord, cost, from_town, to_town) 
                                  for (x, y), (cost, coord, from_town, to_town) 
                                  in buildable_tiles_dict.items()]
        unique_buildable_tiles.sort(key=lambda x: x[1])
        
        paint_used = 0
        
        # Build tiles until we run out of paint
        for coord, track_cost, from_town, to_town in unique_buildable_tiles:
            if paint_used + track_cost <= paint_available:
                actions.append(f"PLACE_TRACKS {coord.x} {coord.y}")
                paint_used += track_cost
                
                # Mark this tile as owned
                tiles[coord.y][coord.x].tracks_owner = self.my_id
            elif paint_used == paint_available:
                # No more paint available, break early
                break
        
        print(f"Built {len(actions)} tracks using {paint_used}/3 paint", file=sys.stderr)
        
        return actions


    def get_disruption_target(self) -> int | None:
        """
        Smart disruption targeting that finds the most valuable region to disrupt.
        Returns region_id to disrupt, or None if no good target.
        """
        foe_id = 1 - self.my_id
        best_target = None
        best_value = -1
        
        tiles = self.grid.tiles  # Cache tiles reference
        
        # Analyze all regions
        for region_id, region in self.region_by_id.items():
            # Skip already inked regions or regions with towns
            if region.inked or region.has_town:
                continue
            
            foe_tracks_count = 0
            my_tracks_count = 0
            active_connections_count = 0
            
            # Quick scan for tracks
            for coord in region.coords:
                tile = tiles[coord.y][coord.x]
                owner = tile.tracks_owner
                
                if owner == foe_id:
                    foe_tracks_count += 1
                    if tile.part_of_active_connections:
                        active_connections_count += len(tile.part_of_active_connections)
                elif owner == self.my_id:
                    my_tracks_count += 1
            
            # Skip if we have tracks or no enemy tracks
            if my_tracks_count > 0 or foe_tracks_count == 0:
                continue
            
            # Calculate disruption value
            disruptions_to_ink = 3 - region.instability
            value = (foe_tracks_count * 2 + 
                    active_connections_count * 5 + 
                    (3 - disruptions_to_ink) * 3)
            
            if value > best_value:
                best_value = value
                best_target = region_id
        
        if best_target is not None:
            print(f"Disruption target: Region {best_target} (value={best_value})", file=sys.stderr)
        
        return best_target
        

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