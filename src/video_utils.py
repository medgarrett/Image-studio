import cv2
import exifread
import numpy as np
from typing import List, Optional, Tuple


def extract_frame_and_exif(
    avi_file_path: str, frame_number: int = 1
) -> Tuple[Optional[np.ndarray], dict]:
    """
    Extracts a specific frame from an AVI file and any available EXIF metadata.
    Returns (frame_as_bgr_array, exif_dict). Both can be None on failure.
    """
    cap = None
    try:
        cap = cv2.VideoCapture(avi_file_path)
        if not cap.isOpened():
            raise IOError(f"Could not open video: {avi_file_path}")

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        if not ret:
            raise IOError(f"Could not read frame {frame_number} from {avi_file_path}")

        exif_data = {}
        with open(avi_file_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            for tag, value in tags.items():
                if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote'):
                    exif_data[str(tag)] = str(value)

        return frame, exif_data

    except Exception as e:
        print(f"[video_utils] Error extracting frame/EXIF: {e}")
        return None, None

    finally:
        if cap is not None:
            cap.release()


def get_video_duration(avi_file_path: str) -> float:
    """Returns video duration in seconds, or 0.0 on error."""
    cap = cv2.VideoCapture(avi_file_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if fps > 0 and total_frames > 0:
            return total_frames / fps
        return 0.0
    finally:
        cap.release()


def extract_frames_at_times(
    avi_file_path: str,
    seconds_list: List[float],
) -> List[Tuple[np.ndarray, float]]:
    """
    Opens the video once and extrae frames en los tiempos solicitados (segundos).
    Devuelve [(frame_bgr, t_seconds), ...]. Omite tiempos que exceden la duración.
    """
    results = []
    cap = None
    try:
        cap = cv2.VideoCapture(avi_file_path)
        if not cap.isOpened():
            raise IOError(f"Could not open video: {avi_file_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0:
            fps = 30.0
        duration = total_frames / fps

        for t in sorted(seconds_list):
            if t > duration + 0.5:
                print(f"[video_utils] t={t}s excede duración {duration:.1f}s, omitiendo.")
                continue
            frame_num = min(int(t * fps), total_frames - 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if ret:
                results.append((frame, t))
            else:
                print(f"[video_utils] No se pudo leer frame en t={t}s (frame {frame_num}).")

    except Exception as e:
        print(f"[video_utils] Error en {avi_file_path}: {e}")

    finally:
        if cap is not None:
            cap.release()

    return results
