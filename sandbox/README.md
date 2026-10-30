# Isolated execution worker

The web app sends only `language`, `code` and `stdin` to the authenticated private worker. The worker chooses all Docker flags and the image; students cannot supply commands, image names, mounts or runtime options. There is no host execution fallback.

Each request gets a disposable container using **gVisor `runsc`**. The container runs as UID 10001, without network access, host mounts, Linux capabilities, or a writable root filesystem. Work and temporary directories are size-limited tmpfs. Limits: 1 CPU, 512 MiB memory, 64 processes, 32 MiB per regular output file, 128 open files. Execution: 5 seconds; compilation: 30 seconds; total worker request: 40 seconds. Output: 128 KiB per stream; the outside worker also caps its received protocol data. The outer worker forcibly removes the container even after a timeout or malformed response. Install the `campus-reaper.timer` template as well: it checks every minute for labeled Campus Code containers older than 90 seconds and removes leftovers after a worker crash.

The web process has no Docker privileges. Only the private runner user can access Docker. Run these on a dedicated execution VM, without unrelated workloads or sensitive host files. gVisor provides another isolation boundary; this is not a claim that container escapes are impossible. Maintain the host, Docker, gVisor and runtime image and perform the real isolation tests before accepting students.

## Linux worker preparation

Follow the official [Docker installation documentation](https://docs.docker.com/engine/install/) and [gVisor installation documentation](https://gvisor.dev/docs/user_guide/install/). Configure Docker's `runsc` runtime using the [gVisor Docker guide](https://gvisor.dev/docs/user_guide/quick_start/docker/).

Build locally from the `sandbox` directory:

```sh
docker build -t campus-sandbox:1 sandbox
docker image inspect --format '{{.Id}}' campus-sandbox:1
```

Set `SANDBOX_IMAGE` to the printed immutable image ID in the runner service environment. An image tag is acceptable during local testing; pin the tested ID before deployment. Rebuild and re-test periodically for security updates. The worker never pulls images while processing a request.

Run the actual execution and isolation tests on that Linux worker:

```sh
SANDBOX_IMAGE=campus-sandbox:1 RUN_SANDBOX_TESTS=1 .venv/bin/python -m unittest discover -s tests -v
```

Tests cover all eight languages, stdin, infinite loops, output floods, memory limits, network denial, root filesystem writes, and per-run temporary filesystem disposal. A skipped test is **not** evidence that isolation works. These tests cannot run on the current machine without the Linux Docker/gVisor worker.

No Docker socket is mounted into student containers. The runner service must stay on loopback or a restricted private network, with authentication; never expose port 8001 to students. For a separate VM, use an authenticated SSH tunnel to the runner's loopback listener, or an HTTPS endpoint restricted to the web server. The web application rejects unencrypted remote worker URLs.
