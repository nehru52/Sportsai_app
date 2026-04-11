"""
Fine-tune MotionAGFormer on volleyball pose sequences.
Auto-temperature monitoring version - pauses when GPU > 80°C
"""
import os, sys, json, numpy as np, torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import time
import threading
import subprocess

BASE_DIR      = "C:/sportsai-backend"
POSE_DIR      = os.path.join(BASE_DIR, "data/pose_data/volleyball")
CKPT_PATH     = os.path.join(BASE_DIR, "models/AthletePose3D/model_params/motionagformer-s-ap3d.pth.tr")
MAGFORMER_DIR = os.path.join(BASE_DIR, "models/VolleyVision/models/MotionAGFormer")
OUTPUT_CKPT   = os.path.join(BASE_DIR, "models/AthletePose3D/model_params/motionagformer-volleyball-finetuned.pth")

N_FRAMES  = 81
N_JOINTS  = 17
STRIDE    = 27
BATCH     = 1
EPOCHS    = 50
LR        = 1e-4
DEVICE    = "cuda" if torch.cuda.is_available() else "cpu"

# Temperature monitoring settings
TEMP_CHECK_INTERVAL = 30  # seconds
TEMP_PAUSE_THRESHOLD = 80  # °C - pause if above
TEMP_RESUME_THRESHOLD = 75  # °C - resume when cooled
COOLDOWN_MINUTES = 5

# COCO skeleton bone pairs for bone length loss
BONES = [
    (0,1),(0,2),(1,3),(2,4),
    (5,6),(5,7),(7,9),(6,8),(8,10),
    (5,11),(6,12),(11,12),
    (11,13),(13,15),(12,14),(14,16),
]

print(f"Device: {DEVICE}")
print(f"Loading data from {POSE_DIR}...")
print(f"Auto-temp monitoring: pause at {TEMP_PAUSE_THRESHOLD}°C, resume at {TEMP_RESUME_THRESHOLD}°C")

# ── Temperature Monitor Thread ───────────────────────────────────────────────

class TemperatureMonitor:
    def __init__(self):
        self.current_temp = 0
        self.should_pause = False
        self.paused = False
        self.running = True
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        
    def start(self):
        self.thread.start()
        print(f"[TEMP MONITOR] Started - checking every {TEMP_CHECK_INTERVAL}s")
        
    def _get_temp(self):
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=temperature.gpu', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            return int(result.stdout.strip())
        except:
            return 0
            
    def _monitor(self):
        while self.running:
            self.current_temp = self._get_temp()
            
            # Check if we need to pause
            if self.current_temp >= TEMP_PAUSE_THRESHOLD and not self.paused:
                self.should_pause = True
                self.paused = True
                print(f"\n{'='*50}")
                print(f"[TEMP ALERT] GPU HOT: {self.current_temp}°C")
                print(f"[TEMP ALERT] Auto-pausing training for {COOLDOWN_MINUTES} min...")
                print(f"{'='*50}\n")
                
            # Check if we can resume
            elif self.current_temp <= TEMP_RESUME_THRESHOLD and self.paused:
                self.should_pause = False
                self.paused = False
                print(f"\n{'='*50}")
                print(f"[TEMP OK] GPU cooled to {self.current_temp}°C")
                print(f"[TEMP OK] Resuming training...")
                print(f"{'='*50}\n")
                
            time.sleep(TEMP_CHECK_INTERVAL)
            
    def check_and_wait(self):
        """Call this in training loop - blocks if too hot"""
        while self.should_pause:
            time.sleep(1)
        return self.current_temp
        
    def stop(self):
        self.running = False

temp_monitor = TemperatureMonitor()

# ── Dataset ───────────────────────────────────────────────────────────────────

class VolleyballPoseDataset(Dataset):
    def __init__(self, sequences):
        self.windows = []
        for seq in sequences:
            T = len(seq)
            padded = _replay_pad(seq, N_FRAMES)
            i = 0
            while i + N_FRAMES <= len(padded):
                win = padded[i:i+N_FRAMES]
                self.windows.append(win.astype(np.float32))
                i += STRIDE
            last = max(0, len(padded) - N_FRAMES)
            if not self.windows or i - STRIDE != last:
                self.windows.append(padded[last:last+N_FRAMES].astype(np.float32))

        print(f"  Dataset: {len(self.windows)} windows from {len(sequences)} sequences")

    def __len__(self):
        return len(self.windows)

    def __getitem__(self, idx):
        win = self.windows[idx]
        norm = win.copy()
        norm[:,:,0] = norm[:,:,0] / 360.0 - 1.0
        norm[:,:,1] = norm[:,:,1] / 360.0 - 1.0
        conf = np.ones((N_FRAMES, N_JOINTS, 1), dtype=np.float32)
        inp  = np.concatenate([norm, conf], axis=2)
        return torch.from_numpy(inp), torch.from_numpy(win)


def _replay_pad(seq, target):
    if len(seq) >= target:
        return seq
    idx = np.arange(target) % len(seq)
    return seq[idx]


# ── Load sequences ────────────────────────────────────────────────────────────

def load_sequences():
    meta = json.load(open(os.path.join(POSE_DIR, "metadata.json")))
    seqs = []
    for r in meta["processed"]:
        path = os.path.join(POSE_DIR, r["technique"], r["pose_file"])
        if not os.path.exists(path):
            continue
        seq = np.load(path).astype(np.float32)
        xy  = seq[:, :, :2]
        if len(xy) >= 20:
            seqs.append(xy)
    print(f"Loaded {len(seqs)} sequences")
    return seqs


# ── Losses ────────────────────────────────────────────────────────────────────

def reprojection_loss(pred3d, orig2d_norm):
    pred2d = pred3d[:, :, :, :2]
    return nn.functional.mse_loss(pred2d, orig2d_norm)


def bone_length_loss(pred3d):
    loss = 0.0
    for i, j in BONES:
        bone = pred3d[:, :, i] - pred3d[:, :, j]
        length = torch.norm(bone, dim=2)
        loss += length.var(dim=1).mean()
    return loss / len(BONES)


def smoothness_loss(pred3d):
    diff = pred3d[:, 1:] - pred3d[:, :-1]
    return (diff ** 2).mean()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Start temperature monitor
    temp_monitor.start()
    
    # Load model
    if MAGFORMER_DIR not in sys.path:
        sys.path.insert(0, MAGFORMER_DIR)
    from model.MotionAGFormer import MotionAGFormer

    model = MotionAGFormer(
        n_layers=26, dim_in=3, dim_feat=64, dim_rep=512, dim_out=3,
        mlp_ratio=4, act_layer=nn.GELU, attn_drop=0., drop=0., drop_path=0.,
        use_layer_scale=True, layer_scale_init_value=1e-5,
        use_adaptive_fusion=True, num_heads=8, qkv_bias=False, qkv_scale=None,
        hierarchical=False, num_joints=N_JOINTS, use_temporal_similarity=True,
        temporal_connection_len=1, use_tcn=False, graph_only=False,
        neighbour_num=2, n_frames=N_FRAMES,
    )

    ckpt  = torch.load(CKPT_PATH, map_location="cpu", weights_only=False)
    state = ckpt.get("model", ckpt.get("state_dict", ckpt))
    state = {k.replace("module.", ""): v for k, v in state.items()}
    model.load_state_dict(state, strict=True)
    model = model.to(DEVICE)
    print("Model loaded on", DEVICE)

    # Data
    seqs    = load_sequences()
    split   = int(len(seqs) * 0.85)
    train_d = VolleyballPoseDataset(seqs[:split])
    val_d   = VolleyballPoseDataset(seqs[split:])
    train_l = DataLoader(train_d, batch_size=BATCH, shuffle=True, num_workers=2, pin_memory=True, persistent_workers=True)
    val_l   = DataLoader(val_d, batch_size=BATCH, shuffle=False, num_workers=2, pin_memory=True, persistent_workers=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_val = float('inf')
    print(f"\nStarting training: {EPOCHS} epochs, batch_size={BATCH}")
    print(f"Auto-pause enabled: training will pause automatically if GPU > {TEMP_PAUSE_THRESHOLD}°C")
    print("="*50)

    for epoch in range(1, EPOCHS + 1):
        # Train
        model.train()
        train_loss = 0.0
        batch_count = 0
        
        for inp, orig2d in train_l:
            # Auto-pause check - blocks here if too hot
            current_temp = temp_monitor.check_and_wait()
            
            # Print temp every 50 batches
            if batch_count % 50 == 0:
                print(f"  [Batch {batch_count}] GPU: {current_temp}°C", end='\r')
            
            inp    = inp.to(DEVICE)
            orig2d = orig2d.to(DEVICE)

            pred = model(inp)

            orig2d_norm = orig2d.clone()
            orig2d_norm[:,:,:,0] = orig2d_norm[:,:,:,0] / 360.0 - 1.0
            orig2d_norm[:,:,:,1] = orig2d_norm[:,:,:,1] / 360.0 - 1.0

            loss = (
                reprojection_loss(pred, orig2d_norm) * 1.0 +
                bone_length_loss(pred)               * 0.5 +
                smoothness_loss(pred)                * 0.1
            )

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item()
            batch_count += 1

        scheduler.step()
        train_loss /= len(train_l)

        # Validate
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for inp, orig2d in val_l:
                inp    = inp.to(DEVICE)
                orig2d = orig2d.to(DEVICE)
                pred   = model(inp)
                orig2d_norm = orig2d.clone()
                orig2d_norm[:,:,:,0] = orig2d_norm[:,:,:,0] / 360.0 - 1.0
                orig2d_norm[:,:,:,1] = orig2d_norm[:,:,:,1] / 360.0 - 1.0
                loss = reprojection_loss(pred, orig2d_norm)
                val_loss += loss.item()
        val_loss /= max(len(val_l), 1)

        print(f"\nEpoch {epoch:3d}/{EPOCHS} | train={train_loss:.4f} | val={val_loss:.4f} | lr={scheduler.get_last_lr()[0]:.2e} | last_temp={temp_monitor.current_temp}°C")

        if val_loss < best_val:
            best_val = val_loss
            torch.save({"model": model.state_dict(), "epoch": epoch, "val_loss": val_loss}, OUTPUT_CKPT)
            print(f"  ✓ Saved best model (val={val_loss:.4f})")

    temp_monitor.stop()
    print(f"\nFine-tuning complete. Best val loss: {best_val:.4f}")
    print(f"Saved to: {OUTPUT_CKPT}")
    print("\nTo use: update CKPT_PATH in pose_3d_lifter.py to point to the new weights")


if __name__ == "__main__":
    main()