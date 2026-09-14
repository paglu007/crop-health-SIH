
import json
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms, models


class RiceDiseaseModel:
    """
    EfficientNet-B0 based rice disease classifier.

    Classes:
    - Bacterial Leaf Blight
    - Brown Spot
    - Healthy Rice Leaf
    - Leaf Blast
    - Leaf scald
    - Sheath Blight
    """

    def __init__(self):
        # ----------------------------------------------------
        # Paths
        # ----------------------------------------------------

        BASE_DIR = Path(__file__).resolve().parents[1]

        self.model_path = (
            BASE_DIR
            / "models"
            / "best_model.pth"
        )

        self.class_names_path = (
            BASE_DIR
            / "models"
            / "class_names.json"
        )

        # ----------------------------------------------------
        # Device
        # ----------------------------------------------------

        self.device = torch.device(
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        print("=" * 60)
        print("Loading Rice Disease AI Model")
        print("=" * 60)

        print(f"Device: {self.device}")

        if torch.cuda.is_available():
            print(
                f"GPU: "
                f"{torch.cuda.get_device_name(0)}"
            )

        # ----------------------------------------------------
        # Check model files
        # ----------------------------------------------------

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model not found:\n"
                f"{self.model_path}"
            )

        if not self.class_names_path.exists():
            raise FileNotFoundError(
                f"Class names not found:\n"
                f"{self.class_names_path}"
            )

        # ----------------------------------------------------
        # Load class names
        # ----------------------------------------------------

        with open(
            self.class_names_path,
            "r",
            encoding="utf-8"
        ) as f:

            self.class_names = json.load(f)

        print(
            f"Classes: {self.class_names}"
        )

        # ----------------------------------------------------
        # Create EfficientNet-B0
        # ----------------------------------------------------

        self.model = models.efficientnet_b0(
            weights=None
        )

        num_classes = len(
            self.class_names
        )

        self.model.classifier[1] = nn.Linear(
            self.model.classifier[1].in_features,
            num_classes
        )

        # ----------------------------------------------------
        # Load trained weights
        # ----------------------------------------------------

        checkpoint = torch.load(
            self.model_path,
            map_location=self.device
        )

        self.model.load_state_dict(
            checkpoint["model_state_dict"]
        )

        self.model = self.model.to(
            self.device
        )

        self.model.eval()

        # ----------------------------------------------------
        # Image preprocessing
        # ----------------------------------------------------

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),

            transforms.ToTensor(),

            transforms.Normalize(
                mean=[
                    0.485,
                    0.456,
                    0.406
                ],

                std=[
                    0.229,
                    0.224,
                    0.225
                ]
            )
        ])

        print("AI model loaded successfully.")
        print("=" * 60)


    def predict(self, image_path):
        """
        Predict rice disease from an image.

        Returns:
            {
                "disease": "...",
                "confidence": 95.23,
                "class_index": 3
            }
        """

        # ----------------------------------------------------
        # Open image
        # ----------------------------------------------------

        image = Image.open(
            image_path
        ).convert("RGB")

        # ----------------------------------------------------
        # Transform image
        # ----------------------------------------------------

        image_tensor = self.transform(
            image
        )

        image_tensor = image_tensor.unsqueeze(
            0
        )

        image_tensor = image_tensor.to(
            self.device
        )

        # ----------------------------------------------------
        # Prediction
        # ----------------------------------------------------

        with torch.no_grad():

            outputs = self.model(
                image_tensor
            )

            probabilities = torch.softmax(
                outputs,
                dim=1
            )

            confidence, predicted = torch.max(
                probabilities,
                dim=1
            )

        class_index = predicted.item()

        confidence_value = (
            confidence.item() * 100
        )

        disease = self.class_names[
            class_index
        ]

        return {
            "disease": disease,

            "confidence": round(
                confidence_value,
                2
            ),

            "class_index": class_index
        }


# ============================================================
# GLOBAL MODEL INSTANCE
# ============================================================

rice_disease_model = RiceDiseaseModel()

