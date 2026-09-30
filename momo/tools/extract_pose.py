#!/usr/bin/env python3
"""Liest mit MediaPipe (Pose Landmarker, "heavy") die Körperpose aus einem Video.

Aufruf:  python extract_pose.py VIDEO.mp4 pose_raw.json [--step 2]
Modell:  pose_heavy.task (https://storage.googleapis.com/mediapipe-models/pose_landmarker/
         pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task), neben dem Skript oder per
         Umgebungsvariable POSE_MODEL.
Ausgabe: JSON mit Bild- und Weltkoordinaten (33 Landmarken) pro verwendetem Frame.
         --step 2 nimmt jeden 2. Frame (aus 60 fps werden 30 fps).
"""
import argparse, json, os
import cv2, mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("out")
ap.add_argument("--step", type=int, default=2)
a = ap.parse_args()

model = os.environ.get("POSE_MODEL") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "pose_heavy.task")
cap = cv2.VideoCapture(a.video)
fps = cap.get(cv2.CAP_PROP_FPS); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
W = cap.get(cv2.CAP_PROP_FRAME_WIDTH); H = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
opts = vision.PoseLandmarkerOptions(
    base_options=mpp.BaseOptions(model_asset_path=model),
    running_mode=vision.RunningMode.VIDEO, num_poses=1,
    min_pose_detection_confidence=0.3, min_pose_presence_confidence=0.3, min_tracking_confidence=0.3)
lm = vision.PoseLandmarker.create_from_options(opts)

frames = []
for i in range(n):
    ok, f = cap.read()
    if not ok:
        break
    if i % a.step:
        continue
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    r = lm.detect_for_video(img, int(i / fps * 1000))
    if r.pose_landmarks:
        frames.append(dict(i=i, t=i / fps,
            img=[[p.x, p.y, p.z, p.visibility] for p in r.pose_landmarks[0]],
            world=[[p.x, p.y, p.z, p.visibility] for p in r.pose_world_landmarks[0]]))
    else:
        frames.append(dict(i=i, t=i / fps, img=None, world=None))

json.dump(dict(fps=fps / a.step, W=W, H=H, frames=frames), open(a.out, "w"))
print("fertig:", len(frames), "Frames,", sum(f["img"] is None for f in frames), "ohne Erkennung")
os._exit(0)  # MediaPipe wirft beim normalen Beenden eine harmlose Exception
