import dlib
import cv2
from scipy.spatial import distance as dist
from imutils import face_utils

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

EAR_THRESHOLD = 0.21
CONSEC_FRAMES = 2

def eye_aspect_ratio(eye):
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

class BlinkDetector:
    def __init__(self):
        self.counter = 0
        self.blinks = 0

    def process_frame(self, gray_frame):
        rects = detector(gray_frame, 0)
        if not rects:
            return {"blinks": self.blinks, "face_detected": False}

        rect = rects[0]
        shape = face_utils.shape_to_np(predictor(gray_frame, rect))
        left_eye = shape[lStart:lEnd]
        right_eye = shape[rStart:rEnd]
        ear = (eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2.0

        if ear < EAR_THRESHOLD:
            self.counter += 1
        else:
            if self.counter >= CONSEC_FRAMES:
                self.blinks += 1
            self.counter = 0

        return {"blinks": self.blinks, "face_detected": True}