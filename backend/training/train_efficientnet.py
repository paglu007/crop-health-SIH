
import os
import json
import random
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms, models


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATASET_DIR = (
    BASE_DIR
    / "dataset"
    / "rice-disease-dataset"
    / "Rice_Leaf_AUG"
)

MODEL_DIR = BASE_DIR / "backend" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "best_model.pth"

# RTX 3050 Laptop GPU - 4 GB VRAM
BATCH_SIZE = 8

EPOCHS = 10
IMAGE_SIZE = 224
LEARNING_RATE = 0.0001

# ============================================================
# GPU / CUDA
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

SEED = 42

random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ============================================================
# START
# ============================================================

print("=" * 60)
print("Rice Disease EfficientNet Training")
print("=" * 60)

print(f"Dataset : {DATASET_DIR}")
print(f"Device  : {DEVICE}")

if torch.cuda.is_available():
    print(f"GPU     : {torch.cuda.get_device_name(0)}")
    print(f"CUDA    : {torch.version.cuda}")

    gpu_memory = torch.cuda.get_device_properties(0).total_memory
    gpu_memory_gb = gpu_memory / (1024 ** 3)

    print(f"VRAM    : {gpu_memory_gb:.2f} GB")

print("=" * 60)


# ============================================================
# CHECK DATASET
# ============================================================

if not DATASET_DIR.exists():
    raise FileNotFoundError(
        f"Dataset folder not found:\n{DATASET_DIR}"
    )


# ============================================================
# IMAGE TRANSFORMS
# ============================================================

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),

    transforms.RandomHorizontalFlip(),

    transforms.RandomRotation(10),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# ============================================================
# LOAD DATASET
# ============================================================

dataset = datasets.ImageFolder(
    root=str(DATASET_DIR),
    transform=transform
)

print(f"\nTotal images: {len(dataset)}")

print("\nClasses:")

for index, class_name in enumerate(dataset.classes):
    print(f"{index}: {class_name}")


# ============================================================
# SAVE CLASS NAMES
# ============================================================

class_names_path = MODEL_DIR / "class_names.json"

with open(class_names_path, "w", encoding="utf-8") as f:
    json.dump(dataset.classes, f, indent=4)

print(f"\nClass names saved to:")
print(class_names_path)


# ============================================================
# TRAIN / VALIDATION SPLIT
# ============================================================

train_size = int(0.8 * len(dataset))
val_size = len(dataset) - train_size

train_dataset, val_dataset = random_split(
    dataset,
    [train_size, val_size],
    generator=torch.Generator().manual_seed(SEED)
)

print(f"\nTraining images  : {len(train_dataset)}")
print(f"Validation images: {len(val_dataset)}")


# ============================================================
# DATA LOADERS
# ============================================================

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=0,
    pin_memory=torch.cuda.is_available()
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,
    pin_memory=torch.cuda.is_available()
)


# ============================================================
# LOAD EFFICIENTNET-B0
# ============================================================

print("\nLoading EfficientNet-B0...")

weights = models.EfficientNet_B0_Weights.DEFAULT

model = models.efficientnet_b0(weights=weights)

# Number of disease classes
num_classes = len(dataset.classes)

# Replace final classifier
model.classifier[1] = nn.Linear(
    model.classifier[1].in_features,
    num_classes
)

model = model.to(DEVICE)

print(f"Number of classes: {num_classes}")


# ============================================================
# LOSS + OPTIMIZER
# ============================================================

criterion = nn.CrossEntropyLoss()

optimizer = torch.optim.Adam(
    model.parameters(),
    lr=LEARNING_RATE
)


# ============================================================
# TRAINING
# ============================================================

best_accuracy = 0.0

print("\nStarting training...")
print("=" * 60)

for epoch in range(EPOCHS):

    # --------------------------------------------------------
    # TRAIN
    # --------------------------------------------------------

    model.train()

    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in train_loader:

        images = images.to(
            DEVICE,
            non_blocking=True
        )

        labels = labels.to(
            DEVICE,
            non_blocking=True
        )

        optimizer.zero_grad()

        outputs = model(images)

        loss = criterion(
            outputs,
            labels
        )

        loss.backward()

        optimizer.step()

        running_loss += loss.item()

        _, predicted = torch.max(
            outputs,
            1
        )

        total += labels.size(0)

        correct += (
            predicted == labels
        ).sum().item()

    train_accuracy = (
        100 * correct / total
    )


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    model.eval()

    val_correct = 0
    val_total = 0
    val_loss = 0.0

    with torch.no_grad():

        for images, labels in val_loader:

            images = images.to(
                DEVICE,
                non_blocking=True
            )

            labels = labels.to(
                DEVICE,
                non_blocking=True
            )

            outputs = model(images)

            loss = criterion(
                outputs,
                labels
            )

            val_loss += loss.item()

            _, predicted = torch.max(
                outputs,
                1
            )

            val_total += labels.size(0)

            val_correct += (
                predicted == labels
            ).sum().item()

    val_accuracy = (
        100 * val_correct / val_total
    )


    # --------------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------------

    print(
        f"Epoch [{epoch + 1}/{EPOCHS}] "
        f"Train Loss: "
        f"{running_loss / len(train_loader):.4f} "
        f"Train Acc: "
        f"{train_accuracy:.2f}% "
        f"Val Loss: "
        f"{val_loss / len(val_loader):.4f} "
        f"Val Acc: "
        f"{val_accuracy:.2f}%"
    )


    # --------------------------------------------------------
    # SAVE BEST MODEL
    # --------------------------------------------------------

    if val_accuracy > best_accuracy:

        best_accuracy = val_accuracy

        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "classes": dataset.classes,
                "num_classes": num_classes
            },
            MODEL_PATH
        )

        print(
            f"  ✓ Best model saved: "
            f"{MODEL_PATH}"
        )


# ============================================================
# FINISHED
# ============================================================

print("\n" + "=" * 60)
print("TRAINING COMPLETE")
print("=" * 60)

print(
    f"Best validation accuracy: "
    f"{best_accuracy:.2f}%"
)

print(
    f"Model saved at: "
    f"{MODEL_PATH}"
)

print(
    f"Classes saved at: "
    f"{class_names_path}"
)

if torch.cuda.is_available():

    print("\nGPU memory summary:")

    allocated = torch.cuda.memory_allocated(0)
    reserved = torch.cuda.memory_reserved(0)

    print(
        f"Allocated: "
        f"{allocated / (1024 ** 3):.2f} GB"
    )

    print(
        f"Reserved : "
        f"{reserved / (1024 ** 3):.2f} GB"
    )

