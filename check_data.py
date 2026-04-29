import numpy as np
import os

actions = ['spike', 'serve', 'block', 'dig']
base = 'data/pose_data/volleyball'

for action in actions:
    folder = os.path.join(base, action)
    if not os.path.exists(folder):
        print(f'{action}: folder missing')
        continue

    npy_files = [f for f in os.listdir(folder) if f.endswith('.npy')]
    valid = []
    too_short = []
    corrupt = []

    for f in npy_files:
        try:
            arr = np.load(os.path.join(folder, f))
            if arr.shape[0] < 30:
                too_short.append((f, arr.shape))
            else:
                valid.append((f, arr.shape))
        except Exception as e:
            corrupt.append(f)

    print(f'\n{action.upper()}:')
    print(f'  Total .npy files : {len(npy_files)}')
    print(f'  Valid (>=30 frames): {len(valid)}')
    print(f'  Too short (<30 frames): {len(too_short)}')
    print(f'  Corrupt: {len(corrupt)}')
    if valid:
        shapes = [v[1] for v in valid]
        print(f'  Sample shape: {shapes[0]}')
        print(f'  Expected: (N, 17, 3) for 3D or (N, 17, 2) for 2D')

print('\n--- METADATA ---')
import json
with open('data/pose_data/volleyball/metadata.json') as f:
    data = json.load(f)
failed = data.get('failed', [])
processed = data.get('processed', [])
print(f'Processed: {len(processed)}')
print(f'Failed: {len(failed)}')
if failed:
    print('First 5 failures:')
    for item in failed[:5]:
        print(' ', item)
print(f'Last updated: {data.get("last_updated")}')