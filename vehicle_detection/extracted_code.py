# Cell 0
import torch

print("PyTorch version:", torch.__version__)
print("GPU available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
else:
    print("WARNING: GPU not available")

# Cell 1
!pip install -q ultralytics

# Cell 2
import ultralytics

print("Ultralytics version:", ultralytics.__version__)

# Cell 3
from ultralytics import YOLO

import torch

print("CUDA:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

# Cell 4
!pip install -q huggingface_hub

# Cell 5
from huggingface_hub import snapshot_download

dataset_path = snapshot_download(
    repo_id="thundarstrom/indian-license-plate-detection",
    repo_type="dataset",
    local_dir="/content/indian_license_plate"
)

print(dataset_path)

# Cell 6
import os

dataset_dir = "/content/indian_license_plate"

for root, dirs, files in os.walk(dataset_dir):
    level = root.replace(dataset_dir, "").count(os.sep)

    if level < 3:
        print("  " * level + os.path.basename(root) + "/")

# Cell 7
import os

dataset_dir = "/content/indian_license_plate"

for root, dirs, files in os.walk(dataset_dir):
    for file in files:
        path = os.path.join(root, file)
        size = os.path.getsize(path)

        print(f"{path}  |  {size / 1024:.2f} KB")

# Cell 8
!rm -rf /content/indian_license_plate

# Cell 9
!pip install -q roboflow

# Cell 10
!pip install roboflow

from roboflow import Roboflow
rf = Roboflow(api_key="umeQWqMUCBgBkmL0Gs0b")
project = rf.workspace("ipd-qy4se").project("indian-license-plate-detection-6tmbr-b9bnb-nfk37")
version = project.version(1)
dataset = version.download("yolov8")


# Cell 11
import os

dataset_path = "/content/Indian-License-Plate-Detection--1"

for root, dirs, files in os.walk(dataset_path):
    level = root.replace(dataset_path, "").count(os.sep)

    if level < 3:
        print("  " * level + os.path.basename(root) + "/")

# Cell 12
yaml_path = "/content/Indian-License-Plate-Detection--1/data.yaml"

with open(yaml_path, "r") as f:
    print(f.read())

# Cell 13
import os

base = "/content/Indian-License-Plate-Detection--1"

for split in ["train", "valid", "test"]:
    image_dir = os.path.join(base, split, "images")
    label_dir = os.path.join(base, split, "labels")

    images = [
        f for f in os.listdir(image_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    labels = [
        f for f in os.listdir(label_dir)
        if f.endswith(".txt")
    ]

    print(f"{split.upper()}")
    print("Images :", len(images))
    print("Labels :", len(labels))
    print("-" * 30)

# Cell 14
import cv2
import random
import os
import matplotlib.pyplot as plt

base = "/content/Indian-License-Plate-Detection--1"

image_dir = os.path.join(base, "train", "images")
label_dir = os.path.join(base, "train", "labels")

image_files = [
    f for f in os.listdir(image_dir)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
]

# Pick a random image
image_name = random.choice(image_files)

image_path = os.path.join(image_dir, image_name)
label_path = os.path.join(
    label_dir,
    os.path.splitext(image_name)[0] + ".txt"
)

# Read image
image = cv2.imread(image_path)
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

height, width, _ = image.shape

# Read YOLO annotation
with open(label_path, "r") as f:
    lines = f.readlines()

for line in lines:

    values = line.strip().split()

    class_id = int(values[0])

    x_center = float(values[1]) * width
    y_center = float(values[2]) * height

    box_width = float(values[3]) * width
    box_height = float(values[4]) * height

    # Convert center coordinates → corner coordinates
    x1 = int(x_center - box_width / 2)
    y1 = int(y_center - box_height / 2)

    x2 = int(x_center + box_width / 2)
    y2 = int(y_center + box_height / 2)

    # Draw bounding box
    cv2.rectangle(
        image,
        (x1, y1),
        (x2, y2),
        (255, 0, 0),
        3
    )

plt.figure(figsize=(12, 8))
plt.imshow(image)
plt.axis("off")
plt.title(f"Training image: {image_name}")
plt.show()

# Cell 15
!pip install -q ultralytics

# Cell 16
from ultralytics import YOLO
import torch

print("GPU available:", torch.cuda.is_available())
print("GPU:", torch.cuda.get_device_name(0))

# Cell 17
from ultralytics import YOLO

model = YOLO("yolo26n.pt")

# Cell 18
results = model.train(
    data="/content/Indian-License-Plate-Detection--1/data.yaml",
    epochs=50,
    imgsz=640,
    batch=16,
    device=0,
    project="/content/IBVAP",
    name="plate_detector"
)

# Cell 19
from ultralytics import YOLO

model = YOLO(
    "/content/IBVAP/plate_detector/weights/best.pt"
)

print("Model loaded successfully!")

# Cell 20
test_results = model.predict(
    source="/content/Indian-License-Plate-Detection--1/test/images",
    conf=0.25,
    save=True
)

# Cell 21
import glob
from IPython.display import Image, display

prediction_files = glob.glob(
    "/content/IBVAP/plate_detector/**/*.jpg",
    recursive=True
)

print("Prediction files found:", len(prediction_files))

for file in prediction_files[:5]:
    print(file)
    display(Image(filename=file))

# Cell 23
import os
import random

test_dir = "/content/Indian-License-Plate-Detection--1/test/images"

image_files = [
    os.path.join(test_dir, f)
    for f in os.listdir(test_dir)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
]

test_image = random.choice(image_files)

print("Testing image:")
print(test_image)

# Cell 24
vehicle_results = vehicle_model.predict(
    source=test_image,
    conf=0.25,
    save=True
)

# Cell 25
from IPython.display import Image, display

display(
    Image(
        filename="/content/runs/detect/predict-2/drop-car-front_1903_jpg.rf.7cab83dfd920ab3a630b13150cb4fcf4.jpg"
    )
)

# Cell 26
import os
import random

test_dir = "/content/Indian-License-Plate-Detection--1/test/images"

images = [
    os.path.join(test_dir, f)
    for f in os.listdir(test_dir)
    if f.lower().endswith((".jpg", ".jpeg", ".png"))
]

sample_images = random.sample(images, min(10, len(images)))

vehicle_results = vehicle_model.predict(
    source=sample_images,
    conf=0.25,
    save=True
)

print("Tested", len(sample_images), "images")

# Cell 27
from ultralytics import YOLO

model = YOLO("/content/IBVAP/plate_detector/weights/best.pt")

metrics = model.val(
    data="/content/Indian-License-Plate-Detection--1/data.yaml",
    split="test",
    imgsz=640,
    device=0
)

# Cell 28
!pip install -q huggingface_hub

# Cell 29
from huggingface_hub import snapshot_download

dataset_path = snapshot_download(
    repo_id="iisc-aim/UVH-26",
    repo_type="dataset",
    local_dir="/content/UVH-26"
)

print("Dataset downloaded to:")
print(dataset_path)

# Cell 30
import os

print("UVH-26 exists:", os.path.exists("/content/UVH-26"))
print("Size currently used:")

!du -sh /content/UVH-26 2>/dev/null || true

# Cell 31
from huggingface_hub import list_repo_files

files = list_repo_files(
    repo_id="iisc-aim/UVH-26",
    repo_type="dataset"
)

print("Total files:", len(files))

for f in files[:100]:
    print(f)

# Cell 32
from huggingface_hub import hf_hub_download

repo = "iisc-aim/UVH-26"

mv_json = hf_hub_download(
    repo_id=repo,
    filename="UVH-26-Train/UVH-26-MV-Train.json",
    repo_type="dataset",
    local_dir="/content/UVH-26"
)

st_json = hf_hub_download(
    repo_id=repo,
    filename="UVH-26-Train/UVH-26-ST-Train.json",
    repo_type="dataset",
    local_dir="/content/UVH-26"
)

print("MV annotations:", mv_json)
print("ST annotations:", st_json)

# Cell 33
import json

with open("/content/UVH-26/UVH-26-Train/UVH-26-MV-Train.json", "r") as f:
    mv_data = json.load(f)

with open("/content/UVH-26/UVH-26-Train/UVH-26-ST-Train.json", "r") as f:
    st_data = json.load(f)

print("MV type:", type(mv_data))
print("ST type:", type(st_data))

if isinstance(mv_data, dict):
    print("MV keys:", mv_data.keys())

if isinstance(st_data, dict):
    print("ST keys:", st_data.keys())

# Cell 34
print("\n--- MV sample ---")
print(str(mv_data)[:3000])

print("\n--- ST sample ---")
print(str(st_data)[:3000])

# Cell 35
print("=== VEHICLE CLASSES ===")

for category in mv_data["categories"]:
    print(category)

# Cell 36
print("Number of images:", len(mv_data["images"]))
print("Number of annotations:", len(mv_data["annotations"]))
print("Number of categories:", len(mv_data["categories"]))

# Cell 37
from collections import Counter

category_names = {
    c["id"]: c["name"]
    for c in mv_data["categories"]
}

counts = Counter(
    ann["category_id"]
    for ann in mv_data["annotations"]
)

print("\n=== ANNOTATIONS PER CLASS ===")

for category_id, count in counts.items():
    print(category_names[category_id], ":", count)

# Cell 38
print("Total MV images:", len(mv_data["images"]))
print("Total MV annotations:", len(mv_data["annotations"]))

# Cell 39
from collections import Counter

image_annotation_count = Counter(
    ann["image_id"] for ann in mv_data["annotations"]
)

counts = list(image_annotation_count.values())

print("Images with annotations:", len(counts))
print("Average vehicles/image:", sum(counts) / len(counts))
print("Maximum vehicles in one image:", max(counts))

# Cell 40
from collections import defaultdict, Counter

# Map image ID → image information
image_info = {
    img["id"]: img
    for img in mv_data["images"]
}

# Map image ID → list of annotations
image_annotations = defaultdict(list)

for ann in mv_data["annotations"]:
    image_annotations[ann["image_id"]].append(ann)

print("Images:", len(image_info))
print("Images with annotations:", len(image_annotations))

# Cell 41
class_image_counts = Counter()

for image_id, annotations in image_annotations.items():
    classes_in_image = set(
        ann["category_id"]
        for ann in annotations
    )

    for class_id in classes_in_image:
        class_image_counts[class_id] += 1

print("Images containing each class:\n")

for category in mv_data["categories"]:
    cid = category["id"]
    name = category["name"]
    print(f"{name:20s}: {class_image_counts[cid]}")

# Cell 42
print("\nRare classes:")

for category in sorted(
    mv_data["categories"],
    key=lambda x: class_image_counts[x["id"]]
):
    print(
        f"{category['name']:20s} "
        f"{class_image_counts[category['id']]} images"
    )

# Cell 43
import random
from collections import defaultdict

random.seed(42)

# Category ID -> class name
category_names = {
    c["id"]: c["name"]
    for c in mv_data["categories"]
}

# Image ID -> annotations
image_annotations = defaultdict(list)

for ann in mv_data["annotations"]:
    image_annotations[ann["image_id"]].append(ann)

# Image ID -> classes present
image_classes = {}

for image_id, anns in image_annotations.items():
    image_classes[image_id] = set(
        ann["category_id"] for ann in anns
    )

# Group images by class
class_images = defaultdict(list)

for image_id, classes in image_classes.items():
    for class_id in classes:
        class_images[class_id].append(image_id)

# Target number of images per class
targets = {
    "Others": 255,
    "Mini-bus": 500,
    "Tempo-traveller": 800,
    "Van": 1000,
    "Bicycle": 1200,
    "MUV": 1800,
    "Bus": 1800,
    "SUV": 1800,
    "Truck": 1800,
    "Sedan": 1800,
    "LCV": 1800,
    "Hatchback": 1800,
    "Three-wheeler": 2000,
    "Two-wheeler": 2500
}

selected_ids = set()

# First guarantee representation of every class
for class_id, name in category_names.items():

    available = class_images[class_id]
    target = targets[name]

    sample_size = min(target, len(available))

    selected = random.sample(available, sample_size)

    selected_ids.update(selected)

print("Selected unique images:", len(selected_ids))

# Cell 44
import random

random.seed(42)

# Start with images containing rare classes
priority_classes = [
    "Others",
    "Mini-bus",
    "Tempo-traveller",
    "Van",
    "Bicycle",
    "MUV",
    "Bus"
]

priority_ids = set()

for class_name in priority_classes:
    class_id = next(
        c["id"] for c in mv_data["categories"]
        if c["name"] == class_name
    )

    available = class_images[class_id]
    priority_ids.update(available)

print("Priority images:", len(priority_ids))

# If priority images > 8000, randomly select 8000 from them
if len(priority_ids) > 8000:
    selected_8000 = set(random.sample(list(priority_ids), 8000))
else:
    selected_8000 = set(priority_ids)

    remaining = list(selected_ids - selected_8000)
    needed = 8000 - len(selected_8000)

    if needed > 0:
        selected_8000.update(
            random.sample(remaining, min(needed, len(remaining)))
        )

print("FINAL SELECTED IMAGES:", len(selected_8000))

# Cell 45
selected_ids = selected_8000

print("Final images:", len(selected_ids))

# Cell 46
import random

random.seed(42)

selected_8000 = set(random.sample(list(selected_ids), 8000))
selected_ids = selected_8000

print("FINAL SELECTED IMAGES:", len(selected_ids))

# Cell 47
import os

base = "/content/IBVAP/vehicle_dataset"

for split in ["train", "val", "test"]:
    os.makedirs(f"{base}/images/{split}", exist_ok=True)
    os.makedirs(f"{base}/labels/{split}", exist_ok=True)

print("Folders created!")

# Cell 48
selected_list = list(selected_ids)
random.shuffle(selected_list)

n = len(selected_list)

train_ids = selected_list[:int(0.80*n)]
val_ids   = selected_list[int(0.80*n):int(0.90*n)]
test_ids  = selected_list[int(0.90*n):]

print("Train:", len(train_ids))
print("Val:", len(val_ids))
print("Test:", len(test_ids))

# Cell 49
from huggingface_hub import hf_hub_download
from tqdm.auto import tqdm
import os

repo = "iisc-aim/UVH-26"

# Build image ID -> filename
image_files = {
    img["id"]: img["file_name"]
    for img in mv_data["images"]
}

all_selected = train_ids + val_ids + test_ids

downloaded = 0
failed = 0

for image_id in tqdm(all_selected):
    filename = image_files[image_id]

    # Find which folder this image belongs to
    if image_id in train_ids:
        split = "train"
    elif image_id in val_ids:
        split = "val"
    else:
        split = "test"

    # Image files are distributed under data/000 etc.
    # Search the repo file list for this filename
    matches = [
        f for f in files
        if f.startswith("UVH-26-Train/data/")
        and f.endswith("/" + filename)
    ]

    if not matches:
        failed += 1
        continue

    try:
        downloaded_file = hf_hub_download(
            repo_id=repo,
            filename=matches[0],
            repo_type="dataset",
            local_dir=f"{base}/images/{split}"
        )
        downloaded += 1

    except Exception:
        failed += 1

print("Downloaded:", downloaded)
print("Failed:", failed)

# Cell 50
import random

random.seed(42)

# Current 8000 selection me se 3000 choose
selected_3000 = set(random.sample(list(selected_ids), 3000))

selected_ids = selected_3000

print("Final selected images:", len(selected_ids))

# Cell 51
selected_list = list(selected_ids)
random.shuffle(selected_list)

train_ids = selected_list[:2400]
val_ids   = selected_list[2400:2700]
test_ids  = selected_list[2700:3000]

print("Train:", len(train_ids))
print("Validation:", len(val_ids))
print("Test:", len(test_ids))

# Cell 52
import os

base = "/content/IBVAP/vehicle_dataset"

for split in ["train", "val", "test"]:
    os.makedirs(f"{base}/images/{split}", exist_ok=True)
    os.makedirs(f"{base}/labels/{split}", exist_ok=True)

print("Dataset folders ready!")

# Cell 53
# filename -> complete Hugging Face path
filename_to_path = {}

for f in files:
    if f.startswith("UVH-26-Train/data/") and f.endswith(".png"):
        filename = os.path.basename(f)
        filename_to_path[filename] = f

print("Image paths found:", len(filename_to_path))

# Cell 54
image_info = {
    img["id"]: img
    for img in mv_data["images"]
}

missing = []

for image_id in selected_ids:
    filename = image_info[image_id]["file_name"]

    if filename not in filename_to_path:
        missing.append(filename)

print("Selected:", len(selected_ids))
print("Missing:", len(missing))

if missing:
    print(missing[:10])

# Cell 55
from concurrent.futures import ThreadPoolExecutor, as_completed
from huggingface_hub import hf_hub_download
from tqdm.auto import tqdm
import os

base = "/content/IBVAP/vehicle_dataset"

# ID -> filename
image_info = {img["id"]: img for img in mv_data["images"]}

# ID -> HF path
selected_paths = {
    image_id: filename_to_path[image_info[image_id]["file_name"]]
    for image_id in selected_ids
}

def download_one(item):
    image_id, hf_path = item

    if image_id in train_ids:
        split = "train"
    elif image_id in val_ids:
        split = "val"
    else:
        split = "test"

    out_dir = f"{base}/images/{split}"
    os.makedirs(out_dir, exist_ok=True)

    try:
        local_file = hf_hub_download(
            repo_id="iisc-aim/UVH-26",
            filename=hf_path,
            repo_type="dataset",
            local_dir=out_dir
        )

        return True, image_id

    except Exception as e:
        return False, (image_id, str(e))

items = list(selected_paths.items())

success = 0
failed = []

with ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(download_one, item) for item in items]

    for future in tqdm(
        as_completed(futures),
        total=len(futures),
        desc="Downloading images"
    ):
        ok, result = future.result()

        if ok:
            success += 1
        else:
            failed.append(result)

print("\n========== DOWNLOAD COMPLETE ==========")
print("Downloaded:", success)
print("Failed:", len(failed))

if failed:
    print("First failures:")
    print(failed[:5])