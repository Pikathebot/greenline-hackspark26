"""GET /api/health (docs/05-BACKEND-SPEC.md §1). Each check is independent
(one failure never fails the whole endpoint); 1.5 s timeout per check."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import docker
import httpx
from docker.errors import DockerException
from fastapi import APIRouter, Request

from greenline.config import Settings

router = APIRouter()

HEALTH_TIMEOUT_S = 1.5


async def _llama_health(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=HEALTH_TIMEOUT_S) as client:
            resp = await client.get(f"{url}/health")
            return resp.status_code == 200
    except Exception:
        return False


def _docker_health(sandbox_image: str) -> tuple[bool, bool]:
    try:
        client = docker.from_env(timeout=HEALTH_TIMEOUT_S)
        client.ping()
    except DockerException:
        return False, False
    try:
        client.images.get(sandbox_image)
        has_image = True
    except DockerException:
        has_image = False
    return True, has_image


def _fixture_repo_seeded(path: Path) -> bool:
    return (path / ".git").exists()


def _gpu_vram_free_mb() -> int | None:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=HEALTH_TIMEOUT_S,
        )
        if result.returncode != 0:
            return None
        return int(result.stdout.strip().splitlines()[0])
    except Exception:
        return None


async def compute_health(settings: Settings) -> dict:
    model_reachable, embed_reachable = await asyncio.gather(
        _llama_health(settings.model_url), _llama_health(settings.embed_url)
    )
    docker_reachable, has_sandbox_image = await asyncio.to_thread(
        _docker_health, settings.sandbox_image
    )
    fixture_seeded = await asyncio.to_thread(_fixture_repo_seeded, settings.fixture_repo_path())
    gpu_free_mb = await asyncio.to_thread(_gpu_vram_free_mb)

    return {
        "modelServer": {
            "url": settings.model_url,
            "reachable": model_reachable,
            "model": settings.model,
        },
        "embedServer": {"url": settings.embed_url, "reachable": embed_reachable},
        "docker": {"reachable": docker_reachable, "sandboxImage": has_sandbox_image},
        "fixtureRepo": {"seeded": fixture_seeded},
        "gpuVramFreeMb": gpu_free_mb,
    }


@router.get("/api/health")
async def health(request: Request) -> dict:
    return await compute_health(request.app.state.settings)
