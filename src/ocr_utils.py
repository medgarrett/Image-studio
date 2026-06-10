import cv2
import cv_algorithms
import pytesseract
import numpy as np


def _preprocess_for_ocr(img_region: np.ndarray, invert: bool = False) -> np.ndarray:
    blurred = cv2.medianBlur(img_region, 3)
    if invert:
        blurred = 255 - blurred
    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    thinned = cv_algorithms.zhang_suen(thresh)
    return 255 - thinned


def read_stealth_cam_metadata(img: np.ndarray, config: dict) -> tuple[str, str]:
    """
    Reads temperature and camera ID overlays from a Stealth Cam frame.
    Returns (tag_temp, tag_cam_id).
    """
    xt, wt = int(config['STEALTH_TEMP']['X']), int(config['STEALTH_TEMP']['W'])
    yt, ht = int(config['STEALTH_TEMP']['Y']), int(config['STEALTH_TEMP']['H'])
    xc, wc = int(config['STEALTH_CAM']['X']),  int(config['STEALTH_CAM']['W'])
    yc, hc = int(config['STEALTH_CAM']['Y']),  int(config['STEALTH_CAM']['H'])

    temp_region = img[yt:yt + ht, xt:xt + wt]
    temp_proc = _preprocess_for_ocr(temp_region, invert=False)
    tag_temp = pytesseract.image_to_string(temp_proc, config="--psm 7").strip()

    cam_region = img[yc:yc + hc, xc:xc + wc]
    cam_proc = _preprocess_for_ocr(cam_region, invert=True)
    tag_cam_id = pytesseract.image_to_string(cam_proc, config="--psm 10").strip()

    return tag_temp, tag_cam_id


def read_stealth_cam_datetime(img: np.ndarray, config: dict) -> str:
    """
    Lee el timestamp del overlay de StealthCam. Devuelve string vacío si falla.
    Las coordenadas se configuran en [STEALTH_TIME] del config.ini.
    """
    try:
        xt = int(config['STEALTH_TIME']['X'])
        wt = int(config['STEALTH_TIME']['W'])
        yt = int(config['STEALTH_TIME']['Y'])
        ht = int(config['STEALTH_TIME']['H'])
        region = img[yt:yt + ht, xt:xt + wt]
        proc = _preprocess_for_ocr(region, invert=False)
        return pytesseract.image_to_string(proc, config="--psm 7").strip()
    except Exception:
        return ''


def read_bushnell_metadata(img: np.ndarray, config: dict) -> tuple[str, str]:
    """
    Reads temperature and camera ID overlays from a Bushnell frame.
    Returns (tag_temp, tag_cam_id).
    """
    xt, wt = int(config['BUSHNELL_TEMP']['X']), int(config['BUSHNELL_TEMP']['W'])
    yt, ht = int(config['BUSHNELL_TEMP']['Y']), int(config['BUSHNELL_TEMP']['H'])
    xc, wc = int(config['BUSHNELL_CAM']['X']),  int(config['BUSHNELL_CAM']['W'])
    yc, hc = int(config['BUSHNELL_CAM']['Y']),  int(config['BUSHNELL_CAM']['H'])

    temp_region = img[yt:yt + ht, xt:xt + wt]
    tag_temp = pytesseract.image_to_string(
        cv2.cvtColor(cv2.medianBlur(temp_region, 3), cv2.COLOR_BGR2GRAY),
        config="--psm 7"
    ).strip()

    cam_region = img[yc:yc + hc, xc:xc + wc]
    tag_cam_id = pytesseract.image_to_string(
        cv2.cvtColor(cv2.medianBlur(cam_region, 3), cv2.COLOR_BGR2GRAY),
        config="--psm 10"
    ).strip()

    return tag_temp, tag_cam_id
