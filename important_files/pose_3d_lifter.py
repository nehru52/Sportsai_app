"""
3D pose lifting: YOLO 2D keypoints → real 3D world coords.
Model: AthletePose3D motionagformer-s-ap3d (n_layers=26, dim_feat=64, n_frames=81)
Fine-tuned on 12 athletic sports — 69% better MPJPE than generic models.

Input:  (T, 17, 2) pixel-space COCO keypoints
Output: (T, 17, 3) 3D keypoints (XY denormalised back to pixels, Z in model units)
"""
import os
import sys
import numpy as np
import torch

BASE_DIR       = "C:/sportsai-backend"
CKPT_PATH      = os.path.join(BASE_DIR, "models/AthletePose3D/model_params/motionagformer-volleyball-finetuned.pth")
MAGFORMER_DIR  = os.path.join(BASE_DIR, "models/VolleyVision/models/MotionAGFormer")

N_FRAMES  = 81
N_JOINTS  = 17
STRIDE    = 27   # N_FRAMES // 3, same as training

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model

    if MAGFORMER_DIR not in sys.path:
        sys.path.insert(0, MAGFORMER_DIR)

    from model.MotionAGFormer import MotionAGFormer

    net = MotionAGFormer(
        n_layers=26,
        dim_in=3,
        dim_feat=64,
        dim_rep=512,
        dim_out=3,
        mlp_ratio=4,
        act_layer=torch.nn.GELU,
        attn_drop=0.,
        drop=0.,
        drop_path=0.,
        use_layer_scale=True,
        layer_scale_init_value=1e-5,
        use_adaptive_fusion=True,
        num_heads=8,
        qkv_bias=False,
        qkv_scale=None,
        hierarchical=False,
        num_joints=N_JOINTS,
        use_temporal_similarity=True,
        temporal_connection_len=1,
        use_tcn=False,
        graph_only=False,
        neighbour_num=2,
        n_frames=N_FRAMES,
    )

    ckpt = torch.load(CKPT_PATH, map_location="cpu")
    # checkpoint may be wrapped
    state = ckpt.get("model", ckpt.get("state_dict", ckpt))
    # strip "module." prefix if saved with DataParallel
    state = {k.replace("module.", ""): v for k, v in state.items()}
    net.load_state_dict(state, strict=True)
    net.eval()
    _model = net
    return _model


def _normalise(pose2d: np.ndarray, img_w: int, img_h: int) -> np.ndarray:
    """Pixel coords → [-1, 1] normalised space (same as AthletePose3D training)."""
    n = pose2d.astype(np.float32).copy()
    n[:, :, 0] = n[:, :, 0] / img_w * 2 - 1
    n[:, :, 1] = n[:, :, 1] / img_h * 2 - (img_h / img_w)
    return n


def _replay_pad(seq: np.ndarray, target: int) -> np.ndarray:
    if len(seq) >= target:
        return seq
    idx = np.arange(target) % len(seq)
    return seq[idx]


def lift_to_3d(
    pose2d: np.ndarray,
    img_w: int,
    img_h: int,
    confidences: np.ndarray | None = None,
) -> np.ndarray:
    """
    Args:
        pose2d:      (T, 17, 2) pixel-space keypoints
        img_w/img_h: frame resolution
        confidences: (T, 17) per-keypoint confidence (optional)

    Returns:
        (T, 17, 3) — XY in pixel space, Z in model-normalised units
    """
    try:
        model = _load_model()
    except Exception as e:
        print(f"[pose_3d_lifter] load failed ({e}), using Z=0 fallback")
        z = np.zeros((*pose2d.shape[:2], 1), dtype=np.float32)
        return np.concatenate([pose2d.astype(np.float32), z], axis=2)

    T = len(pose2d)
    norm2d = _normalise(pose2d, img_w, img_h)           # (T, 17, 2)

    conf = (
        confidences[:, :, None].astype(np.float32)
        if confidences is not None
        else np.ones((T, N_JOINTS, 1), dtype=np.float32)
    )
    inp = np.concatenate([norm2d, conf], axis=2)         # (T, 17, 3)

    # build sliding windows
    padded = _replay_pad(inp, N_FRAMES)                  # at least N_FRAMES long
    windows, positions = [], []
    i = 0
    while i + N_FRAMES <= len(padded):
        windows.append(padded[i : i + N_FRAMES])
        positions.append(i)
        i += STRIDE
    # ensure last frame is always covered
    last_start = max(0, len(padded) - N_FRAMES)
    if not positions or positions[-1] != last_start:
        windows.append(padded[last_start : last_start + N_FRAMES])
        positions.append(last_start)

    out_sum   = np.zeros((T, N_JOINTS, 3), dtype=np.float32)
    out_count = np.zeros(T, dtype=np.float32)

    with torch.no_grad():
        for win, pos in zip(windows, positions):
            x    = torch.from_numpy(win[None])           # (1, 81, 17, 3)
            pred = model(x).squeeze(0).cpu().numpy()     # (81, 17, 3)
            for j in range(N_FRAMES):
                orig = pos + j
                if orig < T:
                    out_sum[orig]   += pred[j]
                    out_count[orig] += 1

    out_count = np.maximum(out_count, 1)
    pose3d = out_sum / out_count[:, None, None]

    # denormalise XY back to pixel space; keep Z as-is
    pose3d[:, :, 0] = (pose3d[:, :, 0] + 1) * img_w / 2
    pose3d[:, :, 1] = (pose3d[:, :, 1] + img_h / img_w) * img_w / 2

    return pose3d
