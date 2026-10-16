# Container Startup Failure — Diagnose, Debug & Recover

A hands-on FastAPI and Docker troubleshooting lab focused on diagnosing a container that starts and immediately exits.

## Lab Goal

Build an intentionally failing FastAPI container, investigate the failure using Docker's built-in debugging tools, identify the root cause, resolve it, and verify the recovered application.

The objective is not to memorize Docker commands.

The objective is to develop a repeatable production troubleshooting mindset:

```text
Container exits
      ↓
Check container state
      ↓
Read logs
      ↓
Inspect exit code
      ↓
Identify PID 1
      ↓
Identify startup command
      ↓
Find root cause
      ↓
Fix application/configuration
      ↓
Rebuild
      ↓
Restart
      ↓
Verify
```

## Folder Structure

```text
container-startup-failure/
│
├── app/
│   └── main.py
│
├── Dockerfile
├── requirements.txt
└── README.md
```

---

# Part 1 — Build the Image

Build the Docker image:

```bash
docker build -t fastapi-startup-failure .
```

Verify that the image exists:

```bash
docker images
```

---

# Part 2 — Reproduce the Crash

The intentionally broken application should contain:

```python
raise RuntimeError("Model configuration is invalid")
```

Add it temporarily below:

```python
print("Starting AI application...")
```

Then run:

```bash
docker run --name startup-failure fastapi-startup-failure
```

The application should start and then immediately terminate.

You have now reproduced a common production problem:

```text
Container starts
      ↓
Application starts
      ↓
Application initialization fails
      ↓
Process exits
      ↓
Container exits
```

---

# Part 3 — Investigate the Failure

## 1. Check Running Containers

```bash
docker ps
```

The failed container is not shown because it is no longer running.

This gives us our first clue:

> The container isn't currently alive.

---

## 2. Check All Containers

```bash
docker ps -a
```

Look for:

```text
Exited (1)
```

The important information is:

```text
Exited (1)
```

The `1` is the container's exit code.

Generally:

```text
0      → successful termination
non-zero → failure
```

Therefore:

```text
Exited (1)
```

means the main process terminated with an error.

---

## 3. Read the Application Logs

```bash
docker logs startup-failure
```

Expected root-cause message:

```text
RuntimeError: Model configuration is invalid
```

This tells us that Docker itself did not necessarily fail.

The application running inside the container failed.

---

# Part 4 — Inspect the Container

## 4. Check the Exit Code

```bash
docker inspect -f '{{.State.ExitCode}}' startup-failure
```

Expected:

```text
1
```

Therefore:

```text
Exit code = 1
```

---

## 5. Check the Container State

```bash
docker inspect -f '{{.State.Status}}' startup-failure
```

Expected:

```text
exited
```

We now know:

```text
Container exists
      ↓
Container is not running
      ↓
Main process exited
```

---

## 6. Find the Command That Actually Ran

```bash
docker inspect -f '{{.Path}} {{range .Args}}{{.}} {{end}}' startup-failure
```

Expected command is approximately:

```text
/usr/local/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

This is important because sometimes the command defined in a Dockerfile is overridden by:

* `docker run`
* Docker Compose
* Kubernetes
* an entrypoint
* a deployment configuration

Always verify what actually executed rather than assuming.

---

# Part 5 — Understand PID 1

The main process of a container normally runs as:

```text
PID 1
```

For a running container:

```bash
docker top <container>
```

You can also inspect processes from inside a running container:

```bash
docker exec <container> ps -ef
```

For the crashed container, the process has already terminated.

The important mental model is:

```text
Docker Container
      │
      └── PID 1: Uvicorn/Python
                    │
                    ├── Application starts
                    │
                    ├── RuntimeError occurs
                    │
                    ├── Process exits
                    │
                    └── Container exits
```

### Why is PID 1 important?

Docker primarily cares about the lifecycle of the container's main process.

If PID 1 terminates:

```text
PID 1 exits
    ↓
Container exits
```

Therefore, when a container immediately disappears from:

```bash
docker ps
```

you should think:

> What happened to the process responsible for keeping this container alive?

---

# Part 6 — Resolve the Problem

Remove the intentional crash from:

```text
app/main.py
```

The resolved application should contain:

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def home():
    return {"message": "FastAPI is working"}


print("Starting AI application...")
```

Rebuild the image:

```bash
docker build -t fastapi-startup-failure .
```

Remove the old failed container:

```bash
docker rm startup-failure
```

Start the resolved application:

```bash
docker run -d \
  --name fastapi-resolved \
  -p 8000:8000 \
  fastapi-startup-failure
```

Check:

```bash
docker ps
```

The container should now be running.

---

# Part 7 — Verify FastAPI

Open:

```text
http://localhost:8000
```

Expected response:

```json
{
  "message": "FastAPI is working"
}
```

Or test from the terminal:

```bash
curl http://localhost:8000
```

---

# Part 8 — Verify the Logs

```bash
docker logs fastapi-resolved
```

You should see Uvicorn startup information similar to:

```text
Uvicorn running on http://0.0.0.0:8000
```

The important difference is now:

```text
Application starts
      ↓
No fatal exception
      ↓
Uvicorn remains alive
      ↓
PID 1 remains alive
      ↓
Container remains running
```

---

# Production Troubleshooting Workflow

When a container starts and immediately exits, follow this workflow:

```text
1. docker ps
       ↓
2. docker ps -a
       ↓
3. docker logs <container>
       ↓
4. docker inspect <container>
       ↓
5. Identify exit code
       ↓
6. Identify PID 1 / startup command
       ↓
7. Find application/configuration problem
       ↓
8. Fix the problem
       ↓
9. Rebuild the image
       ↓
10. Restart and verify
```

This workflow is more important than memorizing individual commands.

---

# Four Questions You Must Be Able to Answer

## Why did it exit?

The main application process crashed because of an unhandled:

```text
RuntimeError
```

during application startup.

## What was PID 1?

The Uvicorn/Python application process.

## What was the exit code?

```text
1
```

indicating that the process terminated because of an error.

## What command actually ran?

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

# Why This Problem Matters for an AI Engineer

This problem is not really about FastAPI.

It represents one of the most common failure patterns in **production AI/ML services**.

A typical AI application might look like:

```text
Client
   ↓
API Gateway
   ↓
FastAPI
   ↓
Model Service
   ↓
LLM / Computer Vision Model
   ↓
GPU
```

When the container starts, the application may perform initialization such as:

```text
Load environment variables
        ↓
Load model configuration
        ↓
Load tokenizer
        ↓
Load model
        ↓
Initialize GPU
        ↓
Connect to Redis/PostgreSQL/Milvus
        ↓
Start API
```

Any one of these steps can fail.

For example:

### Missing model

```text
FileNotFoundError
```

### Incorrect environment variable

```text
KeyError
```

### Invalid model configuration

```text
RuntimeError
```

### CUDA/GPU problem

```text
CUDA error
```

### Dependency incompatibility

```text
ImportError
```

### Database unavailable

```text
Connection refused
```

### Vector database unavailable

```text
Milvus connection failure
```

The resulting production symptom may simply be:

```text
Container
   ↓
Starts
   ↓
Immediately exits
```

Without Docker troubleshooting skills, an AI Engineer may incorrectly conclude:

> "Docker is broken."

With the troubleshooting mindset from this lab, the engineer asks:

```text
Is the container running?
        ↓
What is its state?
        ↓
What did the logs say?
        ↓
What is the exit code?
        ↓
What was PID 1?
        ↓
What command actually executed?
        ↓
What dependency/configuration/model initialization failed?
```

That distinction is extremely important when deploying:

* LLM inference services
* RAG APIs
* Agent systems
* Computer vision APIs
* embedding services
* OCR pipelines
* model servers
* GPU workloads
* FastAPI inference endpoints

---

# The AI Engineer Mental Model

Don't think:

```text
Docker crashed.
```

Think:

```text
Container
    ↓
PID 1
    ↓
AI Application
    ↓
Initialization
    ↓
Model / Config / Dependency / GPU / Database
    ↓
Failure
    ↓
PID 1 exits
    ↓
Container exits
```

Your job as an AI Engineer is to identify **where in this chain the failure occurred**.

---

# Optional Cleanup

Stop the resolved container:

```bash
docker stop fastapi-resolved
```

Remove it:

```bash
docker rm fastapi-resolved
```

Remove the image if required:

```bash
docker rmi fastapi-startup-failure
```

---

# Final Learning Outcome

After completing this lab, you should be able to take a statement like:

> "The AI API container keeps restarting."

and turn it into a concrete investigation:

```text
docker ps
      ↓
docker ps -a
      ↓
docker logs
      ↓
docker inspect
      ↓
Exit code
      ↓
PID 1
      ↓
Actual command
      ↓
Root cause
      ↓
Fix
      ↓
Rebuild
      ↓
Verify
```

**That is the actual skill this lab is designed to teach: debugging the lifecycle of a containerized AI application, not memorizing Docker commands.**
