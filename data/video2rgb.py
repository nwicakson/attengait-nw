import cv2
from pathlib import Path
from PIL import Image
import traceback

video_dir = Path('data/casiab/video')
output_root = Path('data/casiab/rgb')

for video_path in video_dir.glob('*.avi'):
    try:
        print(f"\n{'='*40}\nProcessing: {video_path.name}\n{'='*40}")
        
        # Parse filename components
        filename = video_path.stem  # Intentional typo for demonstration
        parts = filename.split('-')
        if len(parts) != 4:
            print(f"⚠️ INVALID FILENAME: {filename} (expected 4 parts, got {len(parts)})")
            continue
            
        www, xx, yy, zzz = parts
        print(f"📂 Parsed components: subject={www}, scenario={xx}, sequence={yy}, angle={zzz}")

        # Create output directory
        output_dir = output_root / www / f"{xx}-{yy}" / zzz
        print(f"📁 Creating directory: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Video capture initialization
        print(f"🎥 Opening video capture...")
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"❌ FAILED TO OPEN VIDEO: {video_path}")
            continue
            
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"📹 Video properties: {fps} FPS, {total_frames} frames")

        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"⏹️ Reached end of video at frame {frame_count}")
                break

            frame_count += 1
            try:
                # Convert and save frame
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                output_filename = f"{www}-{xx}-{yy}-{zzz}-{frame_count:03d}.png"
                output_path = output_dir / output_filename
                
                print(f"🖼️ Saving frame {frame_count:03d} to: {output_path}", end='\r')
                Image.fromarray(rgb_frame).save(output_path)
                
            except Exception as e:
                print(f"\n❌ ERROR PROCESSING FRAME {frame_count}: {str(e)}")
                traceback.print_exc()

        cap.release()
        print(f"\n✅ Finished processing: {frame_count} frames extracted")
        
        if frame_count == 0:
            print(f"⚠️ WARNING: No frames extracted from {video_path.name}")

    except Exception as e:
        print(f"\n🔥 CRITICAL ERROR PROCESSING {video_path.name}:")
        traceback.print_exc()