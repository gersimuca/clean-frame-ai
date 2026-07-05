# Clean Frame AI

**Clean Frame AI** is an intelligent image dataset cleaning pipeline with React frontend. It uses computer vision and deep learning to automatically filter out corrupt, irrelevant, and poorly framed images from your dataset storing everything in a local SQLite database for easy review and management.

---

## Features

- **Three-Stage Filtering Pipeline**
  - **Corrupt Detection** — Identifies broken, truncated, or malformed image files
  - **Relevance Filter** — Uses OpenAI CLIP to verify image content matches your target category
  - **Framing Filter** — Uses Faster R-CNN to ensure subjects are properly framed

- **Database-First Architecture**
  - All images stored as BLOBs in SQLite — no local file clutter
  - Thumbnails generated automatically for fast browsing
  - Persistent state across restarts

- **Web UI**
  - Upload photos via drag-and-drop or URL
  - Real-time pipeline progress via WebSocket
  - Review invalid images with detailed rejection reasons
  - Batch accept/reject operations
  - Bounding box overlays for detected objects

- **Graceful Hardware Handling**
  - Auto-detects CUDA GPU availability
  - Falls back to CPU if GPU drivers are incompatible

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, WebSocket |
| ML Models | PyTorch, Transformers (CLIP), Torchvision (Faster R-CNN) |
| Database | SQLite with BLOB storage |
| Frontend | React, Tailwind CSS, Recharts |
| Communication | REST API + WebSocket |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- (Optional) NVIDIA GPU with CUDA for faster processing

### 1. Clone and Setup

```bash
git clone https://github.com/gersimuca/clean-frame-ai
cd clean-frame-ai
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd ../frontend
npm install
```

### 4. Run the Application

**Terminal 1 — Backend:**
```bash
cd backend
python main.py
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open your browser to: **http://localhost:5173**

---

## Usage Guide

### Upload Photos

1. Click **"Upload Photos"** in the sidebar
2. Drag and drop images or click to select files
3. Alternatively, paste an image URL and click **Fetch**

### Run the Pipeline

1. Go to **"Pipeline"** in the sidebar
2. Adjust quality thresholds if needed (defaults work well)
3. Toggle processing stages on/off
4. Click **"Start Pipeline"**

### Review Results

| Tab | What You'll See |
|-----|----------------|
| **Accepted** | Clean images that passed all filters |
| **All Invalid** | Every rejected/corrupt image in one view |
| **Corrupt** | Broken files, 0-byte files, unparseable images |
| **Irrelevant** | Images that don't match target content (e.g., cars, food) |
| **Bad Framing** | Target subject too small, cut off, or missing |

Click any image to see:
- Full-size preview
- Rejection reason (for invalid images)
- Quality score
- Detected object bounding boxes
- Metadata

### Batch Operations

- Select multiple images with checkboxes
- **Accept Selected** — Move to accepted
- **Reject Selected** — Move to rejected

---

## Project Structure

```
puralens/
├── backend/
│   ├── main.py                 # FastAPI server
│   ├── config.py               # Settings & GPU detection
│   ├── database.py             # SQLite operations
│   ├── pipeline.py             # Processing pipeline
│   ├── models.py               # Pydantic schemas
│   ├── requirements.txt
│   └── filters/
│       ├── corrupt_filter.py   # Stage 1: File integrity
│       ├── relevance_filter.py # Stage 2: CLIP classification
│       └── framing_filter.py   # Stage 3: Object detection
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── index.css
        ├── context/
        │   └── PipelineContext.jsx
        └── components/
            ├── Layout.jsx
            ├── Sidebar.jsx
            ├── Dashboard.jsx
            ├── UploadPage.jsx
            ├── PipelineControls.jsx
            ├── ImageGrid.jsx
            ├── ImageCard.jsx
            ├── ReviewModal.jsx
            ├── ThresholdSlider.jsx
            ├── BatchActions.jsx
            ├── StatsPanel.jsx
            ├── LogViewer.jsx
            └── ProgressBar.jsx
```

---

## Configuration

Edit `backend/config.py` or set environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PURALENS_DEVICE` | `cuda` | `cuda` or `cpu` |
| `PURALENS_RELEVANCE_THRESHOLD` | `0.30` | CLIP relevance cutoff |
| `PURALENS_DOG_CONFIDENCE` | `0.65` | Object detection confidence |
| `PURALENS_MIN_BOX_RATIO` | `0.03` | Minimum subject size (3% of image) |
| `PURALENS_MAX_BOX_RATIO` | `0.95` | Maximum subject size (95% of image) |
| `PURALENS_MIN_IMAGE_SIZE` | `50` | Minimum dimension in pixels |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload images (multipart/form-data) |
| `POST` | `/api/upload/url` | Fetch image from URL |
| `POST` | `/api/pipeline/start` | Start processing pipeline |
| `POST` | `/api/pipeline/stop` | Stop pipeline |
| `GET` | `/api/stats` | Get processing statistics |
| `GET` | `/api/images?status=` | List images by status |
| `GET` | `/api/images/invalid` | List all invalid images |
| `GET` | `/api/images/{id}` | Get image details |
| `GET` | `/api/images/{id}/full` | Get full image data |
| `GET` | `/api/images/{id}/thumb` | Get thumbnail data |
| `POST` | `/api/images/{id}/accept` | Accept image |
| `POST` | `/api/images/{id}/reject` | Reject image |
| `POST` | `/api/images/{id}/reprocess` | Reset to pending |
| `DELETE` | `/api/images/{id}` | Delete from database |
| `POST` | `/api/clear` | Clear all images |
| `WS` | `/ws/pipeline` | Real-time progress updates |

---

## Troubleshooting

### GPU Driver Issues

If you see `NVIDIA driver too old` errors, the system automatically falls back to CPU. To force CPU mode:

```python
# In backend/config.py
device: str = "cpu"
```

### HuggingFace Rate Limits

Set a token for faster model downloads:

```bash
export HF_TOKEN="your_token_here"
```

### Port Conflicts

Change ports in `backend/config.py` or `frontend/vite.config.js`.

### Database Reset

Delete `puralens.db` in the backend directory to start fresh.

---

## Customization

### Change Target Category

Edit the prompts in `backend/config.py`:

```python
dog_prompts = (
    "a photo of a dog",
    "a photo of a puppy",
    # Add more...
)

not_dog_prompts = (
    "a photo of a person",
    "a photo of a landscape",
    # Add more...
)
```

### Adjust COCO Class

For non-dog subjects, change `self.dog_label` in `backend/filters/framing_filter.py`:

| Class | ID |
|-------|-----|
| Person | 1 |
| Car | 3 |
| Cat | 8 |
| Dog | 18 |
| Horse | 19 |

---

## License

MIT License — feel free to use, modify, and distribute.

---

## Acknowledgments

- [OpenAI CLIP](https://github.com/openai/CLIP) — Vision-language understanding
- [PyTorch](https://pytorch.org/) — Deep learning framework
- [FastAPI](https://fastapi.tiangolo.com/) — Web framework
- [Tailwind CSS](https://tailwindcss.com/) — Utility-first CSS
