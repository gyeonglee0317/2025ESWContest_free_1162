import csv
EMO_AVAILABLE = False
EMO_LABELS = ["Neutral"]
try:
    from model import KeyPointClassifier
    EMO_AVAILABLE = True
except Exception:
    EMO_AVAILABLE = False

class EmotionModule:
    def __init__(self):
        self.enabled = EMO_AVAILABLE
        if self.enabled:
            self.classifier = KeyPointClassifier.KeyPointClassifier() if hasattr(KeyPointClassifier, "KeyPointClassifier") else KeyPointClassifier()
        try:
            with open('model/keypoint_classifier/keypoint_classifier_label.csv', encoding='utf-8-sig') as f:
                EMO_LABELS[:] = [row[0] for row in csv.reader(f)]
        except Exception:
            pass

    @staticmethod
    def calc_landmark_list(image, landmarks):
        h, w = image.shape[:2]
        pts = []
        for lm in landmarks.landmark:
            x = int(min(max(lm.x * w, 0), w - 1))
            y = int(min(max(lm.y * h, 0), h - 1))
            pts.append([x, y])
        return pts

    @staticmethod
    def preprocess(landmark_list):
        import copy, itertools
        tmp = copy.deepcopy(landmark_list)
        base_x, base_y = tmp[0][0], tmp[0][1]
        for i, p in enumerate(tmp):
            tmp[i][0] = p[0] - base_x
            tmp[i][1] = p[1] - base_y
        tmp = list(itertools.chain.from_iterable(tmp))
        maxv = max(list(map(abs, tmp))) if tmp else 1
        if maxv == 0: maxv = 1
        return [v / maxv for v in tmp]

    def infer(self, frame_bgr, face_landmarks):
        if not self.enabled or face_landmarks is None:
            return "Neutral"
        lm_list = self.calc_landmark_list(frame_bgr, face_landmarks)
        feat = self.preprocess(lm_list)
        try:
            emo_id = self.classifier(feat)
            if 0 <= emo_id < len(EMO_LABELS): return EMO_LABELS[emo_id]
        except Exception:
            pass
        return "Neutral"
