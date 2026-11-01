import sys
from typing import List, Tuple

def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            disk_map = f.read().strip()
    except FileNotFoundError:
        raise
    
    # Parse the disk map to extract files and their lengths
    # Files are at even indices (0, 2, 4, ...), free space at odd indices (1, 3, 5, ...)
    files = []  # List of (id, length)
    file_lengths = []  # file_lengths[id] = length
    free_space_lengths = []  # List of free space lengths in order
    total_blocks = 0
    
    file_id = 0
    for i, char in enumerate(disk_map):
        length = int(char)
        if i % 2 == 0:  # File
            files.append((file_id, length))
            file_id += 1
        else:  # Free space
            free_space_lengths.append(length)
        total_blocks += length
    
    max_file_id = file_id - 1
    
    # Calculate initial positions of each file
    file_pos = [0] * file_id
    pos = 0
    for i, char in enumerate(disk_map):
        length = int(char)
        if i % 2 == 0:  # File
            file_id_idx = i // 2
            file_pos[file_id_idx] = pos
        pos += length
    
    # Build list of free segments: (start, length)
    free_segments = []
    pos = 0
    for i, char in enumerate(disk_map):
        length = int(char)
        if i % 2 == 1:  # Free space
            free_segments.append([pos, length])
        pos += length
    
    # Sort free segments by start position
    free_segments.sort(key=lambda x: x[0])
    
    def merge_segments(segs):
        """Merge adjacent free segments and sort by start position."""
        if not segs:
            return []
        segs.sort(key=lambda x: x[0])
        merged = [segs[0][:]]  # Copy first segment
        for seg in segs[1:]:
            last = merged[-1]
            # Check if last segment ends exactly where this one starts
            if last[0] + last[1] == seg[0]:
                last[1] += seg[1]
            else:
                merged.append(seg[:])
        return merged
    
    # Process files in decreasing ID order (from max_file_id down to 1)
    for fid in range(max_file_id, 0, -1):
        L = files[fid][1]
        cur_start = file_pos[fid]
        
        # Find the leftmost free segment that is strictly to the left of cur_start
        # and has length >= L
        target_idx = -1
        for i, seg in enumerate(free_segments):
            seg_start, seg_len = seg[0], seg[1]
            if seg_start < cur_start and seg_len >= L:
                target_idx = i
                break
        
        if target_idx != -1:
            s, l = free_segments[target_idx][0], free_segments[target_idx][1]
            
            # Move the file to position s
            file_pos[fid] = s
            
            # Update free segments
            remaining = l - L
            
            # Modify or remove the used segment
            if remaining > 0:
                # Segment shrinks from the front
                free_segments[target_idx] = [s + L, remaining]
            else:
                # Segment is fully consumed
                free_segments.pop(target_idx)
            
            # Add new free segment at the old position of the file
            free_segments.append([cur_start, L])
            
            # Re-sort and merge free segments
            free_segments = merge_segments(free_segments)
    
    # Calculate the checksum
    checksum = 0
    for fid in range(file_id):
        L = files[fid][1]
        start = file_pos[fid]
        # Sum of positions from start to start+L-1
        # = L * start + (0 + 1 + ... + L-1)
        # = L * start + L * (L - 1) / 2
        sum_positions = L * start + (L * (L - 1)) // 2
        checksum += fid * sum_positions
    
    return checksum

if __name__ == '__main__':
    print(solve())