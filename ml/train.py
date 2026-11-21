"""Rebuild the public benchmark and the frozen, unlabelled workshop queue."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlretrieve
from zipfile import ZipFile

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, confusion_matrix
from sklearn.model_selection import train_test_split
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
URL = "https://archive.ics.uci.edu/static/public/421/aps+failure+at+scania+trucks.zip"
CHECKSUM = "5504d0402f54faaf97ac0ca085a621645763f5cfea2eb29c592b057d43d4db89"


def read_split(archive, split):
    with archive.open(f"aps_failure_{split}_set.csv") as stream:
        for index, line in enumerate(stream):
            if line.startswith(b"class,"):
                break
        else:
            raise ValueError("Missing CSV header")
    with archive.open(f"aps_failure_{split}_set.csv") as stream:
        frame = pd.read_csv(stream, skiprows=index, na_values="na")
    labels = frame.pop("class")
    if not labels.isin(["pos", "neg"]).all():
        raise ValueError("Unexpected target")
    return frame, labels.eq("pos").to_numpy()


def counts(labels, selected):
    tn, fp, fn, tp = map(int, confusion_matrix(labels, selected, labels=[False, True]).ravel())
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, cost=10*fp + 500*fn,
                recall=round(tp / max(1, tp+fn), 4),
                precision=round(tp / max(1, tp+fp), 4))


def threshold_from_validation(scores, labels):
    order = np.argsort(-scores, kind="stable")
    levels, hits = scores[order], labels[order].cumsum()
    ends = np.flatnonzero(np.r_[levels[:-1] != levels[1:], True])
    costs = 10*(ends+1-hits[ends]) + 500*(labels.sum()-hits[ends])
    if 500*labels.sum() <= costs.min():
        return float(np.nextafter(levels[0], np.inf))
    return float(levels[ends[costs.argmin()]])


def save_json(name, payload):
    path = ROOT / "data" / name
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run(path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != CHECKSUM:
        raise ValueError("Archive checksum differs from the pinned UCI version")
    with ZipFile(path) as archive:
        features, target = read_split(archive, "training")
        train, valid = train_test_split(np.arange(len(target)), test_size=.2,
                                        stratify=target, random_state=42)
        model = HistGradientBoostingClassifier(max_iter=120, max_leaf_nodes=15,
                    learning_rate=.08, l2_regularization=1, early_stopping=False, random_state=42)
        model.fit(features.iloc[train], target[train])
        cutoff = threshold_from_validation(model.predict_proba(features.iloc[valid])[:, 1], target[valid])
        test, truth = read_split(archive, "test")
    scores = model.predict_proba(test)[:, 1]
    selected = scores >= cutoff
    rank = np.argsort(-scores, kind="stable")
    capacity = len(scores) // 20
    metrics = dict(train=len(train), validation=len(valid), test=len(test), positives=int(truth.sum()),
        cutoff=cutoff, model=counts(truth, selected),
        inspect_none=counts(truth, np.zeros_like(truth)), inspect_all=counts(truth, np.ones_like(truth)),
        average_precision=round(float(average_precision_score(truth, scores)), 4),
        prevalence=round(float(truth.mean()), 4), top_5pct=dict(slots=capacity,
        captured=int(truth[rank[:capacity]].sum()), recall=round(float(truth[rank[:capacity]].sum()/truth.sum()), 4)))
    save_json("evaluation.json", metrics)
    queue = []
    for i in range(160):
        queue.append(dict(id=f"RF-{i+1:03}", score=round(float(scores[i]), 7),
                          flagged=bool(selected[i]), missing=int(test.iloc[i].isna().sum())))
    save_json("shift.json", queue)
    folder = ROOT / ".cache"
    folder.mkdir(exist_ok=True)
    joblib.dump(dict(model=model, cutoff=cutoff, features=list(features)), folder / "aps.joblib")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    archive_path = args.archive or ROOT / ".cache" / "aps.zip"
    if not archive_path.is_file() and args.archive is None:
        archive_path.parent.mkdir(exist_ok=True)
        urlretrieve(URL, archive_path)
    with threadpool_limits(limits=3):
        run(archive_path)

