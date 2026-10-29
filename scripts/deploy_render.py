import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen


PENDING_STATUSES = {
    "created",
    "queued",
    "build_in_progress",
    "pre_deploy_in_progress",
    "update_in_progress",
}


def request_json(url, api_key=None, payload=None):
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()

    request = Request(url, data=data, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"HTTP request failed with status {error.code}.") from None
    except (URLError, OSError, ValueError):
        raise RuntimeError("Request failed or returned invalid JSON.") from None


def wait_for_deployment(deploy_url, api_key, commit_sha, timeout=900):
    deadline = time.monotonic() + timeout
    previous_status = None
    while time.monotonic() < deadline:
        deployment = request_json(deploy_url, api_key)
        status = deployment.get("status")
        if status != previous_status:
            print(f"Render deployment status: {status}", flush=True)
            previous_status = status
        if status == "live":
            if deployment.get("commit", {}).get("id") != commit_sha:
                raise RuntimeError("The live deployment does not match the tested commit.")
            return
        if status not in PENDING_STATUSES:
            raise RuntimeError(f"Render deployment did not succeed: {status}.")
        time.sleep(10)
    raise RuntimeError("Timed out waiting for Render deployment to become live.")


def verify_health(service_url, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = request_json(f"{service_url}/api/health/")
            if response == {"status": "ok"}:
                print("Public health endpoint verified.", flush=True)
                return
        except RuntimeError:
            pass
        time.sleep(5)
    raise RuntimeError("Public health endpoint did not return the expected JSON.")


def main():
    required_variables = (
        "RENDER_API_KEY",
        "RENDER_SERVICE_ID",
        "RENDER_SERVICE_URL",
        "GITHUB_SHA",
    )
    missing = [name for name in required_variables if not os.environ.get(name, "").strip()]
    if missing:
        raise RuntimeError(f"Missing required configuration: {', '.join(missing)}.")

    service_url = os.environ["RENDER_SERVICE_URL"].strip().rstrip("/")
    parsed_url = urlsplit(service_url)
    if (
        parsed_url.scheme != "https"
        or not parsed_url.hostname
        or parsed_url.username
        or parsed_url.password
        or parsed_url.path
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise RuntimeError("RENDER_SERVICE_URL must be an HTTPS origin without a path.")

    api_key = os.environ["RENDER_API_KEY"]
    service_id = quote(os.environ["RENDER_SERVICE_ID"].strip(), safe="")
    commit_sha = os.environ["GITHUB_SHA"]
    deploys_url = f"https://api.render.com/v1/services/{service_id}/deploys"
    deployment = request_json(deploys_url, api_key, {"commitId": commit_sha})
    deploy_id = deployment.get("id")
    if not deploy_id:
        raise RuntimeError("Render did not return a deployment ID.")

    print(f"Requested deployment of tested commit {commit_sha}.", flush=True)
    deploy_url = f"{deploys_url}/{quote(deploy_id, safe='')}"
    wait_for_deployment(deploy_url, api_key, commit_sha)
    verify_health(service_url)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as error:
        print(f"Deployment failed: {error}", file=sys.stderr)
        sys.exit(1)
