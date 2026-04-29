#!/usr/bin/env python3
"""
Quick fix script for critical SportsAI backend errors
Run this before starting the server
"""
import os
import sys
from pathlib import Path

def fix_elite_api_path():
    """Fix hardcoded path in elite_api.py"""
    file_path = Path("elite_api.py")
    if not file_path.exists():
        print("⚠️  elite_api.py not found")
        return
    
    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            content = file_path.read_text(encoding='latin-1')
        except:
            print("⚠️  Could not read elite_api.py (encoding issue)")
            return
    
    old_line = 'sys.path.insert(0, "C:/sportsai-backend/data_collection")'
    new_lines = '''BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "data_collection"))'''
    
    if old_line in content:
        # Add import os if not present
        if 'import os' not in content:
            content = 'import os\n' + content
        content = content.replace(old_line, new_lines)
        file_path.write_text(content, encoding='utf-8')
        print("✅ Fixed elite_api.py hardcoded path")
    else:
        print("✅ elite_api.py already fixed or not using hardcoded path")

def check_virtual_memory():
    """Check if virtual memory is sufficient"""
    try:
        import psutil
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        print(f"\n💾 Memory Status:")
        print(f"   RAM: {vm.total // (1024**3)} GB total, {vm.available // (1024**3)} GB available")
        print(f"   Swap: {swap.total // (1024**3)} GB total, {swap.free // (1024**3)} GB free")
        
        if swap.total < 16 * (1024**3):
            print("\n⚠️  WARNING: Virtual memory < 16 GB")
            print("   This may cause PyTorch CUDA loading errors")
            print("   Increase virtual memory in Windows settings:")
            print("   1. Win + Pause/Break → Advanced system settings")
            print("   2. Performance Settings → Advanced → Virtual Memory")
            print("   3. Set Initial: 16384 MB, Maximum: 32768 MB")
            print("   4. Restart computer")
            return False
        else:
            print("✅ Virtual memory sufficient")
            return True
    except ImportError:
        print("\n⚠️  Cannot check memory (psutil not installed)")
        print("   Install with: pip install psutil")
        return None

def check_pytorch():
    """Check PyTorch installation"""
    try:
        import torch
        print(f"\n🔥 PyTorch Status:")
        print(f"   Version: {torch.__version__}")
        print(f"   CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"   CUDA version: {torch.version.cuda}")
            print(f"   GPU: {torch.cuda.get_device_name(0)}")
        else:
            print("   Running on CPU (slower but works)")
        return True
    except ImportError:
        print("\n❌ PyTorch not installed!")
        print("   Install with: pip install torch torchvision")
        return False
    except Exception as e:
        print(f"\n⚠️  PyTorch error: {e}")
        return False

def check_required_files():
    """Check if required files exist"""
    required = [
        "data_collection/yolo11x-pose.pt",
        "config/volleyball_techniques.json",
    ]
    
    missing = []
    for file_path in required:
        if not Path(file_path).exists():
            missing.append(file_path)
    
    if missing:
        print("\n❌ MISSING REQUIRED FILES:")
        for f in missing:
            print(f"   - {f}")
        print("\n   Download YOLO model:")
        print("   https://github.com/ultralytics/assets/releases/download/v0.0.0/yolo11x-pose.pt")
        return False
    else:
        print("✅ All required files present")
        return True

def create_directories():
    """Create required directories"""
    dirs = [
        "data/annotated_videos",
        "data/match_outputs",
        "data/recruiter_outputs",
        "data/reports",
        "data/frames",
    ]
    
    created = []
    for dir_path in dirs:
        path = Path(dir_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(dir_path)
    
    if created:
        print(f"✅ Created {len(created)} directories")
    else:
        print("✅ All required directories exist")

def check_dependencies():
    """Check critical dependencies"""
    critical_deps = [
        'fastapi',
        'uvicorn',
        'opencv-cv2',
        'numpy',
        'ultralytics',
    ]
    
    missing = []
    for dep in critical_deps:
        try:
            __import__(dep.replace('-', '_'))
        except ImportError:
            missing.append(dep)
    
    if missing:
        print("\n❌ MISSING DEPENDENCIES:")
        for dep in missing:
            print(f"   - {dep}")
        print(f"\n   Install with: pip install {' '.join(missing)}")
        return False
    else:
        print("✅ All critical dependencies installed")
        return True

def fix_database_path():
    """Fix database path in .env"""
    env_path = Path(".env")
    if not env_path.exists():
        print("⚠️  .env file not found")
        return
    
    try:
        content = env_path.read_text(encoding='utf-8')
    except:
        content = env_path.read_text(encoding='latin-1')
    
    old_line = "DATABASE_URL=sqlite:///data/match_processing.db"
    
    if old_line in content:
        # Get absolute path
        abs_path = Path("data/match_processing.db").absolute()
        new_line = f"DATABASE_URL=sqlite:///{abs_path}"
        content = content.replace(old_line, new_line)
        env_path.write_text(content, encoding='utf-8')
        print("✅ Fixed database path in .env")
    else:
        print("✅ Database path already absolute or not found")

def main():
    print("="*60)
    print("🔧 SportsAI Backend - Critical Error Fixes")
    print("="*60)
    
    all_good = True
    
    # Run checks and fixes
    print("\n📋 Running diagnostics...\n")
    
    fix_elite_api_path()
    
    if not check_dependencies():
        all_good = False
    
    if not check_required_files():
        all_good = False
    
    create_directories()
    fix_database_path()
    
    vm_ok = check_virtual_memory()
    if vm_ok is False:
        all_good = False
    
    if not check_pytorch():
        all_good = False
    
    print("\n" + "="*60)
    if all_good:
        print("✅ ALL CHECKS PASSED - Ready to start server!")
        print("="*60)
        print("\nNext steps:")
        print("1. Run: python complete_web_server_fixed.py")
        print("2. Open: http://localhost:8080")
        print("3. Test: Upload a volleyball video")
    else:
        print("⚠️  SOME ISSUES FOUND - Fix them before starting")
        print("="*60)
        print("\nReview the warnings above and:")
        print("1. Install missing dependencies")
        print("2. Download missing model files")
        print("3. Increase virtual memory if needed")
        print("4. Run this script again to verify")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
