import numpy as np

class HeatmapGenerator:
    """
    Generates spatial distribution heatmaps for athletes and teams on the court.
    """
    def __init__(self, frame_w: int, frame_h: int, grid_cols: int = 10, grid_rows: int = 6):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.grid_cols = grid_cols
        self.grid_rows = grid_rows
        
        self.grids = {} # track_id -> np.array

    def update(self, track_id: int, bbox_cx: float, bbox_cy: float):
        if track_id not in self.grids:
            self.grids[track_id] = np.zeros((self.grid_rows, self.grid_cols), dtype=np.float32)
            
        # Map to grid cell
        col = min(int(bbox_cx / self.frame_w * self.grid_cols), self.grid_cols - 1)
        row = min(int(bbox_cy / self.frame_h * self.grid_rows), self.grid_rows - 1)
        
        # Clamp to bounds
        col = max(0, col)
        row = max(0, row)
        
        self.grids[track_id][row, col] += 1

    def get_heatmap(self, track_id: int) -> np.ndarray:
        if track_id not in self.grids:
            return np.zeros((self.grid_rows, self.grid_cols), dtype=np.float32)
            
        grid = self.grids[track_id]
        total = np.sum(grid)
        return grid / total if total > 0 else grid

    def get_team_heatmap(self, track_ids: list) -> np.ndarray:
        combined = np.zeros((self.grid_rows, self.grid_cols), dtype=np.float32)
        found = False
        for tid in track_ids:
            if tid in self.grids:
                combined += self.grids[tid]
                found = True
        
        total = np.sum(combined)
        return combined / total if total > 0 else combined

    def to_dict(self, track_id: int) -> dict:
        heatmap = self.get_heatmap(track_id)
        
        # Determine peak zone
        peak_idx = np.unravel_index(np.argmax(heatmap, axis=None), heatmap.shape)
        row, col = peak_idx
        
        # Mapping row/col to zone name
        v_zone = "mid"
        if row < self.grid_rows / 3: v_zone = "front"
        elif row > 2 * self.grid_rows / 3: v_zone = "back"
        
        h_zone = "centre"
        if col < self.grid_cols / 3: h_zone = "left"
        elif col > 2 * self.grid_cols / 3: h_zone = "right"
        
        return {
            "grid_rows": self.grid_rows,
            "grid_cols": self.grid_cols,
            "data": heatmap.tolist(),
            "peak_zone": f"{v_zone}-{h_zone}"
        }
