def solve() -> int:
    with open('input.txt') as f:
        disk_map_str = f.read().strip()
    
    # Parse the disk map into a list of blocks
    disk = []
    file_id = 0
    for i, char in enumerate(disk_map_str):
        if not char.isdigit():
            continue
        length = int(char)
        if i % 2 == 0:
            # File block
            disk.extend([file_id] * length)
            file_id += 1
        else:
            # Free space
            disk.extend([None] * length)
    
    # Compaction: move blocks one at a time from the end to the leftmost free space
    # Use two pointers: left pointer for free spaces, right pointer for file blocks
    left = 0
    right = len(disk) - 1
    
    while left < right:
        # Find the leftmost free space
        while left < right and disk[left] is not None:
            left += 1
        
        # Find the rightmost file block
        while left < right and disk[right] is None:
            right -= 1
        
        if left >= right:
            break
        
        # Move the block from right to left
        disk[left] = disk[right]
        disk[right] = None
        left += 1
    
    # Calculate checksum
    checksum = 0
    for i, val in enumerate(disk):
        if val is not None:
            checksum += i * val
    
    return checksum

if __name__ == '__main__':
    print(solve())