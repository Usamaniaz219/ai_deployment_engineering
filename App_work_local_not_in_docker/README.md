# Lab: "Works on my machine" — Dockerizing a Python AI app (FastAPI)

This is a deliberately broken mini-project. It behaves perfectly when you run
it directly on your machine, and breaks in several different ways once you
put it in Docker. The goal is to reproduce each failure, read the error
carefully, and fix it — one bug at a time.

There are **4 separate bugs** stacked on top of each other. You'll likely
hit them in order, fix one, rebuild, and hit the next.

## Part 1 — Run it locally (should work)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python train_model.py           # creates models/image_classifier.pkl
python app.py
```

In another terminal:

```bash
curl http://127.0.0.1:5000/health
```

You should get `{"status": "ok"}`. This confirms the app is fully functional
outside Docker.

## Part 2 — Run it in Docker (should NOT work, yet)

```bash
docker build -t ai-lab .
docker run -p 5000:5000 ai-lab
```

Watch what happens. Then, from another terminal:

```bash
curl http://localhost:5000/health
```

## Your job

Diagnose and fix each failure you hit, rebuilding between fixes:

```bash
docker build -t ai-lab .
docker run -p 5000:5000 ai-lab
```

Useful commands while you investigate:

```bash
docker logs <container_id>
docker exec -it <container_id> sh
docker run -it --entrypoint sh ai-lab      # poke around without starting the app
```

Ask yourself, for each failure:
- Does the error happen at *build* time or *run* time?
- Is this an environment difference (OS, Python version, installed libs)?
- Is this a files-not-present problem?
- Is this a networking/config problem?

If you get stuck, `SOLUTION.md` walks through the full diagnosis for all
four bugs. Try not to open it until you've at least reproduced each error
yourself — that's the actual skill being practiced here.
