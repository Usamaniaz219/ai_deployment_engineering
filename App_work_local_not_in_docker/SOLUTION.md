# Solution walkthrough

Four independent bugs, each representative of a *category* of "works
locally, breaks in Docker" problem. Real-world container debugging is
almost always one of these four categories.

---

## Bug 1 — Missing OS-level shared libraries (build succeeds, container crashes on start)

**Symptom:**
```
ImportError: libGL.so.1: cannot open shared object file: No such file or directory
```
(happens on `import cv2`, right after `docker run`)

**Why it happens locally but not in Docker:**
Your local machine (or venv) almost certainly already has the graphics
libraries `opencv-python` links against — they came with your OS, your
desktop environment, or a previous install. `python:3.11-slim` is a
minimal Debian image and does **not** ship `libGL.so.1` or
`libglib2.0-0`. `pip install opencv-python` installs the Python wheel, but
the wheel still dynamically links to system `.so` files that aren't there.

**How to diagnose:**
- The error is an `ImportError` for a `.so` file, not a Python package —
  that's the signature of a missing *system* dependency, not a missing
  *pip* dependency.
- `docker run -it --entrypoint sh ai-lab` then `python -c "import cv2"`
  reproduces it in isolation.

**Fix (two valid options):**
1. Install the missing system libraries in the Dockerfile:
   ```dockerfile
   RUN apt-get update && apt-get install -y --no-install-recommends \
       libgl1 libglib2.0-0 \
       && rm -rf /var/lib/apt/lists/*
   ```
2. Or, better for a headless server context: swap the dependency to
   `opencv-python-headless`, which doesn't need GUI-related libraries at all.

---

## Bug 2 — `.env` never reaches the container (build succeeds, container crashes on start)

**Symptom:**
```
KeyError: 'APP_SECRET_KEY'
```

**Why it happens locally but not in Docker:**
Locally, `python-dotenv` reads `.env` from disk and populates
`os.environ` for you. `.env` is (correctly) listed in `.dockerignore`, so
it's never copied into the image — that part is good practice, since you
don't want secrets baked into an image layer. But nobody arranged for the
variable to reach the container a different way, so it's simply absent at
runtime.

**How to diagnose:**
- `docker exec -it <container_id> sh` then `printenv | grep APP_SECRET`
  shows it's missing.
- `docker exec -it <container_id> sh` then `ls -la` shows no `.env` file in
  `/app`.

**Fix:** pass it in at `docker run` time instead of baking it into the image:
```bash
docker run -p 5000:5000 --env-file .env ai-lab
# or:
docker run -p 5000:5000 -e APP_SECRET_KEY=super-secret-local-dev-key ai-lab
```
In Compose, this is `env_file:` or `environment:`. In production, this
would come from your orchestrator's secrets manager, not a `.env` file at all.

---

## Bug 3 — Model file silently excluded from the build context (build succeeds, container crashes on start)

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'models/image_classifier.pkl'
```

**Why it happens locally but not in Docker:**
`.dockerignore` contains `*.pkl`. That pattern was presumably added to
keep stray local artifacts out of the image, but it also excludes the one
`.pkl` file the app actually needs at runtime. Locally, the file is just
sitting on disk from when you ran `train_model.py`, so `app.py` finds it
fine. In Docker, `COPY . .` never copies it in, because `.dockerignore`
filters the build context *before* `COPY` ever sees it.

**How to diagnose:**
- `docker exec -it <container_id> sh` then `ls models/` shows the
  directory is empty.
- `docker build` with a temporary `RUN find /app -name "*.pkl"` step (or
  just `RUN ls -la models/` right after `COPY . .`) shows the file never
  made it into the image.

**Fix:** remove `*.pkl` from `.dockerignore` (or be more specific — e.g.
ignore a `notebooks/` or `experiments/` folder instead of every `.pkl` in
the repo), so the model artifact your app depends on is actually shipped.
Longer-term, many teams instead build the model in a dedicated pipeline
step or mount it as a volume, rather than relying on it being present in
the build context at all.

---

## Bug 4 — Bound to `127.0.0.1` instead of `0.0.0.0` (container runs, but is unreachable)

**Symptom:** the container stays up, `docker logs` shows the app started
fine, but from the host:
```
curl: (56) Recv failure: Connection reset by peer
```
or a hang / connection refused, even with `-p 5000:5000`.

**Why it happens locally but not in Docker:**
`127.0.0.1` means "only accept connections that originate from this exact
network namespace." Locally, your browser/curl and the Flask process share
the same network namespace, so it works. Inside Docker, the container has
its *own* network namespace — `docker run -p 5000:5000` forwards traffic
from the host into the container's network interface, but that traffic
doesn't originate from `127.0.0.1` *inside* the container, so Flask
refuses it.

**How to diagnose:**
- `docker exec -it <container_id> sh` then `curl 127.0.0.1:5000/health`
  works *from inside* the container — proving the app itself is fine and
  this is a networking/binding issue, not an app crash.
- `curl localhost:5000/health` from the host fails — the gap between
  "works inside, fails from outside" is the tell.

**Fix:** bind to all interfaces inside the container:
```python
uvicorn.run(app, host="0.0.0.0", port=5000)
```

---

## The general pattern

Every "works locally, not in Docker" bug falls into one of these buckets:
1. **Missing OS packages** the local machine already had.
2. **Missing environment/config** that local tooling (`.env`, shell profile) supplied invisibly.
3. **Missing files** due to `.dockerignore`, build context, or working directory assumptions.
4. **Networking** differences from running in an isolated namespace.

When you hit a new failure, the fastest triage question is: *"Did this
fail at build time or run time, and would `docker exec` into a running
container let me reproduce it manually?"* That single habit resolves most
container debugging sessions.
