"""Re-train the repo's dual-head BirdCNN using v2 Maracuyá audio data.

This script:
  1. Loads audio files from v2's folder structure (Estres/, Feliz/)
  2. Preprocesses using the REPO's pipeline (bandpass, HPSS, mel 128×128)
  3. Maps binary labels → soft multi-class labels via label_mapper
  4. Trains the exact BirdCNN architecture from bird_classifier.py
  5. Outputs weights to backend/app/ml/weights/bird_classifier.weights.h5
  6. Generates evaluation metrics and plots

Usage:
    cd backend
    python -m app.ml.training.train_from_v2_data \
        --data-dir /path/to/Archivos_audio \
        --output-dir ./app/ml/weights \
        --augment

The --data-dir must contain subdirectories:
    Estres/   → WAV files labeled as stress (binary_label=0)
    Feliz/    → WAV files labeled as happy (binary_label=1)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, sosfiltfilt
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Constants matching the repo ────────────────────────
SR = 22050
SEGMENT_DURATION = 3.0
N_MELS = 128
SPEC_TIME_FRAMES = 128
BIRD_FREQ_LOW = 800
BIRD_FREQ_HIGH = 10000
RANDOM_STATE = 42


# ── Preprocessing (matches repo's AudioProcessor) ─────

def bandpass_filter(y: np.ndarray, sr: int, low_hz: int, high_hz: int) -> np.ndarray:
    nyquist = sr / 2.0
    low = max(low_hz / nyquist, 0.001)
    high = min(high_hz / nyquist, 0.999)
    if low >= high:
        return y
    sos = butter(4, [low, high], btype="band", output="sos")
    return sosfiltfilt(sos, y).astype(np.float32)


def preprocess_segment_for_repo(y: np.ndarray, sr: int = SR) -> np.ndarray:
    """Process a segment exactly as the repo's BirdCNN._prepare_input expects.

    Returns mel spectrogram of shape (N_MELS, SPEC_TIME_FRAMES) in dB scale,
    min-max normalized to [0,1].
    """
    import librosa

    # Bandpass filter to bird vocal range
    y_filtered = bandpass_filter(y, sr, BIRD_FREQ_LOW, BIRD_FREQ_HIGH)

    # HPSS — keep harmonic component
    y_harmonic, _ = librosa.effects.hpss(y_filtered)

    # Mel spectrogram in dB
    mel = librosa.feature.melspectrogram(
        y=y_harmonic, sr=sr, n_mels=N_MELS, fmax=sr // 2
    )
    mel_db = librosa.power_to_db(mel, ref=np.max)

    # Pad/crop time dimension to SPEC_TIME_FRAMES
    if mel_db.shape[1] < SPEC_TIME_FRAMES:
        pad_width = SPEC_TIME_FRAMES - mel_db.shape[1]
        mel_db = np.pad(mel_db, ((0, 0), (0, pad_width)), mode="constant")
    elif mel_db.shape[1] > SPEC_TIME_FRAMES:
        mel_db = mel_db[:, :SPEC_TIME_FRAMES]

    # Min-max normalize to [0, 1] (same as BirdCNN._prepare_input)
    vmin = mel_db.min()
    vmax = mel_db.max()
    if vmax - vmin > 1e-6:
        mel_db = (mel_db - vmin) / (vmax - vmin)
    else:
        mel_db = np.zeros_like(mel_db)

    return mel_db.astype(np.float32)


# ── Dataset building ───────────────────────────────────

def build_dataset(
    data_dir: str,
    segment_duration: float = SEGMENT_DURATION,
    overlap: float = 0.5,
    rms_threshold: float = 0.008,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load audio files, segment, preprocess, and return X + binary labels + RMS values.

    Returns:
        X: shape (N, N_MELS, SPEC_TIME_FRAMES) — mel spectrograms
        y: shape (N,) — binary labels (0=estres, 1=feliz)
        rms: shape (N,) — RMS energy per segment
    """
    import librosa
    import noisereduce as nr

    estres_dir = os.path.join(data_dir, "Estres")
    feliz_dir = os.path.join(data_dir, "Feliz")

    X_list, y_list, rms_list = [], [], []
    segment_samples = int(segment_duration * SR)
    step = int(segment_samples * (1 - overlap))

    for label, folder in [(0, estres_dir), (1, feliz_dir)]:
        if not os.path.isdir(folder):
            logger.warning("Carpeta no encontrada: %s", folder)
            continue

        wav_files = sorted([
            f for f in os.listdir(folder)
            if f.lower().endswith(".wav")
        ])
        logger.info("Carpeta %s: %d archivos WAV", folder, len(wav_files))

        for fname in wav_files:
            fpath = os.path.join(folder, fname)
            try:
                y_audio, _ = librosa.load(fpath, sr=SR, mono=True)
                y_audio = librosa.util.normalize(y_audio)
                y_audio = nr.reduce_noise(y=y_audio, sr=SR, prop_decrease=0.7)
            except Exception:
                logger.warning("Error cargando %s, saltando", fpath)
                continue

            # Segment with overlap
            for start in range(0, len(y_audio) - segment_samples + 1, step):
                seg = y_audio[start : start + segment_samples]

                # Filter silence
                rms = float(librosa.feature.rms(y=seg).mean())
                if rms < rms_threshold:
                    continue

                # Preprocess for the repo's CNN
                mel = preprocess_segment_for_repo(seg, SR)
                X_list.append(mel)
                y_list.append(label)
                rms_list.append(rms)

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)
    rms = np.array(rms_list, dtype=np.float32)

    logger.info(
        "Dataset: %d segmentos (estres=%d, feliz=%d)",
        len(y), (y == 0).sum(), (y == 1).sum(),
    )
    return X, y, rms


# ── Data Augmentation ──────────────────────────────────

def augment_spectrograms(
    X: np.ndarray, y_mood: np.ndarray, y_voc: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Augment on mel spectrograms: time-shift, freq-mask, noise."""
    X_aug, mood_aug, voc_aug = [X], [y_mood], [y_voc]

    for i in range(len(X)):
        spec = X[i]

        # Time shift ±10%
        shift = int(spec.shape[1] * 0.1 * np.random.uniform(-1, 1))
        shifted = np.roll(spec, shift, axis=1)
        X_aug.append(shifted)
        mood_aug.append(y_mood[i])
        voc_aug.append(y_voc[i])

        # Frequency masking (mask 5-15 mel bands)
        freq_masked = spec.copy()
        n_mask = np.random.randint(5, 16)
        f_start = np.random.randint(0, max(1, spec.shape[0] - n_mask))
        freq_masked[f_start : f_start + n_mask, :] = 0
        X_aug.append(freq_masked)
        mood_aug.append(y_mood[i])
        voc_aug.append(y_voc[i])

        # Gaussian noise
        noise = np.random.normal(0, 0.02, spec.shape).astype(np.float32)
        noisy = np.clip(spec + noise, 0.0, 1.0)
        X_aug.append(noisy)
        mood_aug.append(y_mood[i])
        voc_aug.append(y_voc[i])

    return (
        np.array(X_aug, dtype=np.float32),
        np.array(mood_aug, dtype=np.float32),
        np.array(voc_aug, dtype=np.float32),
    )


# ── Model (imported from repo) ─────────────────────────

def build_model():
    """Build the exact same model as backend/app/ml/bird_classifier.py."""
    import tensorflow as tf

    VOCALIZATION_LABELS = [
        "singing", "chattering", "alarm", "silence",
        "distress", "contact_call", "beak_grinding",
    ]
    MOOD_LABELS = ["happy", "relaxed", "stressed", "scared", "sick", "neutral"]

    inp = tf.keras.Input(shape=(N_MELS, SPEC_TIME_FRAMES, 1), name="mel_input")

    # Shared backbone (MUST match bird_classifier.py exactly)
    x = tf.keras.layers.Conv2D(32, (3, 3), padding="same", activation="relu")(inp)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.MaxPooling2D((2, 2))(x)
    x = tf.keras.layers.Dropout(0.25)(x)

    x = tf.keras.layers.Conv2D(64, (3, 3), padding="same", activation="relu")(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.MaxPooling2D((2, 2))(x)
    x = tf.keras.layers.Dropout(0.25)(x)

    x = tf.keras.layers.Conv2D(128, (3, 3), padding="same", activation="relu")(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.MaxPooling2D((2, 2))(x)
    x = tf.keras.layers.Dropout(0.3)(x)

    x = tf.keras.layers.Conv2D(128, (3, 3), padding="same", activation="relu")(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.4)(x)

    shared = tf.keras.layers.Dense(256, activation="relu", name="shared_dense")(x)

    # Vocalization head
    voc_dense = tf.keras.layers.Dense(128, activation="relu")(shared)
    voc_out = tf.keras.layers.Dense(
        len(VOCALIZATION_LABELS), activation="softmax", name="vocalization"
    )(voc_dense)

    # Mood head
    mood_dense = tf.keras.layers.Dense(128, activation="relu")(shared)
    mood_out = tf.keras.layers.Dense(
        len(MOOD_LABELS), activation="softmax", name="mood"
    )(mood_dense)

    model = tf.keras.Model(inputs=inp, outputs=[voc_out, mood_out])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss={
            "vocalization": "categorical_crossentropy",
            "mood": "categorical_crossentropy",
        },
        loss_weights={"vocalization": 1.0, "mood": 0.8},
        metrics={"vocalization": "accuracy", "mood": "accuracy"},
    )
    return model


# ── Evaluation ─────────────────────────────────────────

def evaluate_and_save(
    model, X_test, y_mood_test, y_voc_test, y_binary_test, output_dir: str,
):
    """Run evaluation, save plots and metrics."""
    import tensorflow as tf

    MOOD_LABELS = ["happy", "relaxed", "stressed", "scared", "sick", "neutral"]
    VOC_LABELS = ["singing", "chattering", "alarm", "silence", "distress", "contact_call", "beak_grinding"]

    X_input = X_test[..., np.newaxis]
    voc_pred, mood_pred = model.predict(X_input, verbose=0)

    # Top-1 predictions
    mood_pred_idx = np.argmax(mood_pred, axis=1)
    mood_true_idx = np.argmax(y_mood_test, axis=1)
    voc_pred_idx = np.argmax(voc_pred, axis=1)
    voc_true_idx = np.argmax(y_voc_test, axis=1)

    # Classification reports
    mood_report = classification_report(
        mood_true_idx, mood_pred_idx,
        target_names=MOOD_LABELS, digits=3, zero_division=0,
    )
    voc_report = classification_report(
        voc_true_idx, voc_pred_idx,
        target_names=VOC_LABELS, digits=3, zero_division=0,
    )

    logger.info("Mood Classification Report:\n%s", mood_report)
    logger.info("Vocalization Classification Report:\n%s", voc_report)

    # Confusion matrices
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    cm_mood = confusion_matrix(mood_true_idx, mood_pred_idx)
    axes[0].imshow(cm_mood, cmap="Blues")
    axes[0].set_title("Mood Confusion Matrix")
    axes[0].set_xticks(range(len(MOOD_LABELS)))
    axes[0].set_xticklabels(MOOD_LABELS, rotation=45, ha="right", fontsize=8)
    axes[0].set_yticks(range(len(MOOD_LABELS)))
    axes[0].set_yticklabels(MOOD_LABELS, fontsize=8)
    for i in range(cm_mood.shape[0]):
        for j in range(cm_mood.shape[1]):
            axes[0].text(j, i, str(cm_mood[i, j]), ha="center", va="center", fontsize=10)

    cm_voc = confusion_matrix(voc_true_idx, voc_pred_idx)
    axes[1].imshow(cm_voc, cmap="Greens")
    axes[1].set_title("Vocalization Confusion Matrix")
    axes[1].set_xticks(range(len(VOC_LABELS)))
    axes[1].set_xticklabels(VOC_LABELS, rotation=45, ha="right", fontsize=8)
    axes[1].set_yticks(range(len(VOC_LABELS)))
    axes[1].set_yticklabels(VOC_LABELS, fontsize=8)
    for i in range(cm_voc.shape[0]):
        for j in range(cm_voc.shape[1]):
            axes[1].text(j, i, str(cm_voc[i, j]), ha="center", va="center", fontsize=10)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "evaluation_plots.png"), dpi=150)
    plt.close()

    # Binary accuracy (the original v2 metric: feliz vs estrés)
    # Map mood predictions back to binary: happy/relaxed → feliz, stressed/scared/sick → estrés
    feliz_moods = {0, 1}  # happy, relaxed
    estres_moods = {2, 3, 4}  # stressed, scared, sick
    binary_pred = np.array([
        1 if idx in feliz_moods else (0 if idx in estres_moods else -1)
        for idx in mood_pred_idx
    ])
    valid = binary_pred >= 0
    if valid.sum() > 0:
        binary_acc = float((binary_pred[valid] == y_binary_test[valid]).mean())
        logger.info("Binary accuracy (feliz/estrés mapping): %.4f", binary_acc)
    else:
        binary_acc = 0.0

    # Save metadata
    metadata = {
        "binary_accuracy": round(binary_acc, 4),
        "mood_accuracy": round(float((mood_pred_idx == mood_true_idx).mean()), 4),
        "voc_accuracy": round(float((voc_pred_idx == voc_true_idx).mean()), 4),
        "test_samples": int(len(X_test)),
        "mood_labels": MOOD_LABELS,
        "vocalization_labels": VOC_LABELS,
        "note": "Trained from v2 binary data with soft label mapping. "
                "Accuracy is limited to covered classes (happy, stressed, neutral).",
    }
    with open(os.path.join(output_dir, "training_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    return metadata


# ── Main ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Train the repo's BirdCNN using v2 Maracuyá audio data"
    )
    parser.add_argument(
        "--data-dir", required=True,
        help="Carpeta raíz con subcarpetas Estres/ y Feliz/",
    )
    parser.add_argument(
        "--output-dir", default="./app/ml/weights",
        help="Carpeta para guardar pesos y artefactos",
    )
    parser.add_argument("--augment", action="store_true", help="Data augmentation")
    parser.add_argument("--epochs", type=int, default=80, help="Max epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Lazy imports (heavy)
    import tensorflow as tf
    tf.random.set_seed(RANDOM_STATE)
    np.random.seed(RANDOM_STATE)

    from label_mapper import build_soft_labels

    # ── 1. Build dataset ───────────────────────────────
    logger.info("Building dataset from %s ...", args.data_dir)
    X, y_binary, rms_values = build_dataset(args.data_dir)

    if len(X) == 0:
        logger.error("No se encontraron segmentos. Verifica que --data-dir contenga Estres/ y Feliz/ con WAVs.")
        sys.exit(1)

    # ── 2. Map to soft multi-class labels ──────────────
    y_mood, y_voc = build_soft_labels(y_binary, rms_values)
    logger.info("Soft labels: mood=%s, voc=%s", y_mood.shape, y_voc.shape)

    # ── 3. Train/test split ────────────────────────────
    indices = np.arange(len(X))
    train_idx, test_idx = train_test_split(
        indices, test_size=0.2, random_state=RANDOM_STATE, stratify=y_binary,
    )

    X_train, X_test = X[train_idx], X[test_idx]
    y_mood_train, y_mood_test = y_mood[train_idx], y_mood[test_idx]
    y_voc_train, y_voc_test = y_voc[train_idx], y_voc[test_idx]
    y_binary_test = y_binary[test_idx]

    logger.info("Train: %d, Test: %d", len(train_idx), len(test_idx))

    # ── 4. Augmentation ────────────────────────────────
    if args.augment:
        X_train, y_mood_train, y_voc_train = augment_spectrograms(
            X_train, y_mood_train, y_voc_train
        )
        logger.info("Post-augmentation: %d samples", len(X_train))

    # ── 5. Add channel dimension ───────────────────────
    X_train_4d = X_train[..., np.newaxis]
    X_test_4d = X_test[..., np.newaxis]

    # ── 6. Build model ─────────────────────────────────
    model = build_model()
    model.summary(print_fn=logger.info)

    # ── 7. Train ───────────────────────────────────────
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=10, restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=4, min_lr=1e-6,
        ),
    ]

    history = model.fit(
        X_train_4d,
        {"vocalization": y_voc_train, "mood": y_mood_train},
        validation_data=(
            X_test_4d,
            {"vocalization": y_voc_test, "mood": y_mood_test},
        ),
        epochs=args.epochs,
        batch_size=args.batch_size,
        callbacks=callbacks,
        verbose=1,
    )

    # ── 8. Save weights ────────────────────────────────
    weights_path = os.path.join(args.output_dir, "bird_classifier.weights.h5")
    model.save_weights(weights_path)
    logger.info("Weights saved to: %s", weights_path)

    # Also save full model for debugging
    model_path = os.path.join(args.output_dir, "bird_classifier_full.keras")
    model.save(model_path)
    logger.info("Full model saved to: %s", model_path)

    # ── 9. Training curves ─────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot(history.history["loss"], label="Train")
    axes[0].plot(history.history["val_loss"], label="Val")
    axes[0].set_title("Total Loss")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    if "mood_accuracy" in history.history:
        axes[1].plot(history.history["mood_accuracy"], label="Train Mood")
        axes[1].plot(history.history["val_mood_accuracy"], label="Val Mood")
    if "vocalization_accuracy" in history.history:
        axes[1].plot(history.history["vocalization_accuracy"], label="Train Voc", linestyle="--")
        axes[1].plot(history.history["val_vocalization_accuracy"], label="Val Voc", linestyle="--")
    axes[1].set_title("Accuracy")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(args.output_dir, "training_curves.png"), dpi=150)
    plt.close()

    # ── 10. Evaluate ───────────────────────────────────
    metadata = evaluate_and_save(
        model, X_test, y_mood_test, y_voc_test, y_binary_test, args.output_dir,
    )

    logger.info("✅ Training complete. Weights at: %s", weights_path)
    logger.info(
        "To activate the CNN in the ensemble, copy the weights file to:\n"
        "  backend/app/ml/weights/bird_classifier.weights.h5\n"
        "The ensemble will automatically shift from Statistical=0.65 → CNN=0.50"
    )


if __name__ == "__main__":
    main()
