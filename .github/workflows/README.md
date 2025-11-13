# GitHub Actions Workflows

This directory contains CI/CD workflows for the Cortana Vision project.

## Reusable Workflow

### `reusable-python-service.yml`

A reusable workflow for building, testing, and deploying Python/uv services. This workflow provides:

- **Python 3.12 setup** (configurable)
- **uv dependency caching** for faster CI runs
- **Automated testing** with pytest and coverage reporting
- **Docker build and push** to GitHub Container Registry (GHCR)
- **Multi-tag strategy** (sha, branch, pr, semver, latest)
- **Optional FFmpeg installation** for services that need it

#### Usage

Create a workflow file for your service (e.g., `.github/workflows/my-service.yml`):

```yaml
name: my-service • build & push

on:
  push:
    branches: [production, development]
    paths:
      - "services/my-service/**"
      - "cortana_common/**"
      - ".github/workflows/my-service.yml"
      - ".github/workflows/reusable-python-service.yml"
  pull_request:
    paths:
      - "services/my-service/**"
      - "cortana_common/**"
  workflow_dispatch: {}

concurrency:
  group: my-service-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    uses: ./.github/workflows/reusable-python-service.yml
    with:
      service_name: my-service
      service_path: services/my-service
      python_version: "3.12"
      install_ffmpeg: false  # Set to true for transcode/sampler/clip services
      run_tests: true
      docker_build: true
```

#### Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `service_name` | Name of the service (e.g., `api-gateway`) | Yes | - |
| `service_path` | Path to service directory (e.g., `services/api-gateway`) | Yes | - |
| `python_version` | Python version to use | No | `3.12` |
| `install_ffmpeg` | Install FFmpeg for testing | No | `false` |
| `run_tests` | Run pytest tests | No | `true` |
| `docker_build` | Build and push Docker image | No | `true` |
| `docker_registry` | Docker registry to push to | No | `ghcr.io` |

#### Features

##### 1. Dependency Caching

The workflow caches uv dependencies using a composite key:
- OS (`ubuntu-latest`)
- Python version
- `uv.lock` file hash

This reduces dependency installation time from ~30s to ~5s on cache hits.

##### 2. Test Execution

Tests are run with pytest and coverage reporting:
```bash
uv sync
uv run pytest -v --cov --cov-report=term --cov-report=xml
```

Coverage reports are uploaded to Codecov (if configured) for PR comments and tracking.

##### 3. Docker Build

Docker images are built with:
- **BuildKit** for faster builds
- **GitHub Actions cache** for layer caching
- **Multi-platform support** (optional)

##### 4. Image Tagging Strategy

Images are tagged with:
- `sha-{full-commit-sha}` - Immutable reference for deployments
- `{branch-name}` - Latest build for branch (e.g., `development`, `production`)
- `pr-{number}` - Pull request builds
- `{semver}` - Semantic version tags (e.g., `v1.2.3`, `1.2`)
- `latest` - Only on default branch

Example tags for a commit on `development` branch:
```
ghcr.io/pasogott/cortana-vision-api-gateway:sha-abc123def456...
ghcr.io/pasogott/cortana-vision-api-gateway:development
```

##### 5. FFmpeg Support

Services that require FFmpeg (transcode-worker, sampler-worker, clip-service) can enable it:

```yaml
with:
  install_ffmpeg: true
```

This installs FFmpeg via apt before running tests.

## Service-Specific Workflows

### `api-gateway.yml`

CI/CD for the API Gateway service. Builds and pushes to `ghcr.io/pasogott/cortana-vision-api-gateway`.

**Triggers:**
- Push to `production` or `development` branches
- Pull requests modifying `services/api-gateway/**`
- Manual workflow dispatch

### `s3-cron-scanner.yml` (Example)

Example workflow using the reusable workflow for the S3 Cron Scanner service.

**Triggers:**
- Push to `production` or `development` branches
- Pull requests modifying `services/s3-cron-scanner/**` or `cortana_common/**`
- Manual workflow dispatch

## Path Filtering

Workflows use path filters to only run when relevant files change:

```yaml
paths:
  - "services/my-service/**"      # Service-specific code
  - "cortana_common/**"            # Shared package changes
  - ".github/workflows/my-service.yml"  # Workflow changes
  - ".github/workflows/reusable-python-service.yml"  # Reusable workflow changes
```

This prevents unnecessary CI runs and saves compute time.

## Concurrency Control

Each workflow uses concurrency groups to cancel in-progress runs when new commits are pushed:

```yaml
concurrency:
  group: my-service-${{ github.ref }}
  cancel-in-progress: true
```

This ensures only the latest commit is being built at any time.

## Permissions

Workflows require these permissions:
- `contents: read` - Read repository contents
- `packages: write` - Push to GitHub Container Registry
- `id-token: write` - OIDC token for registry authentication

## Best Practices

### 1. Always Include cortana_common in Path Filters

Since all services depend on `cortana_common`, include it in path filters:

```yaml
paths:
  - "services/my-service/**"
  - "cortana_common/**"
```

### 2. Use Semantic Versioning for Releases

Tag releases with semantic versions:
```bash
git tag v1.2.3
git push origin v1.2.3
```

This automatically creates versioned Docker images.

### 3. Test Locally Before Pushing

Run tests locally with uv:
```bash
cd services/my-service
uv sync
uv run pytest -v
```

### 4. Use SHA Tags for Deployments

In Kubernetes manifests, reference images by SHA for immutability:
```yaml
image: ghcr.io/pasogott/cortana-vision-api-gateway:sha-abc123def456...
```

### 5. Monitor Build Times

Check GitHub Actions dashboard for build times. If builds are slow:
- Verify uv cache is working (should see "Cache restored" in logs)
- Consider splitting large services
- Review test execution time

## Troubleshooting

### Cache Not Working

If uv cache isn't restoring:
1. Check that `uv.lock` exists in service directory
2. Verify cache key matches in workflow
3. Clear cache in repository settings if corrupted

### Docker Build Fails

Common issues:
- Missing dependencies in `pyproject.toml`
- Dockerfile references wrong paths
- Build context doesn't include required files

### Tests Fail in CI But Pass Locally

Check:
- Python version matches (3.12 in CI)
- Environment variables are set correctly
- Test database/services are available (use mocks if needed)

## Adding a New Service

1. Create service directory: `services/my-service/`
2. Add `pyproject.toml`, `uv.lock`, `Dockerfile`
3. Create workflow file: `.github/workflows/my-service.yml`
4. Copy example from `s3-cron-scanner.yml` and update service name/path
5. Push and verify workflow runs successfully

## Migration from Old Workflows

To migrate an existing service workflow:

1. **Backup** existing workflow file
2. **Replace** with reusable workflow call (see example above)
3. **Update** path filters to include `cortana_common/**`
4. **Test** with a pull request
5. **Verify** Docker images are tagged correctly

Example migration for `api-gateway.yml`:

**Before:**
```yaml
jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      # ... many more steps
```

**After:**
```yaml
jobs:
  build:
    uses: ./.github/workflows/reusable-python-service.yml
    with:
      service_name: api-gateway
      service_path: services/api-gateway
      python_version: "3.12"  # Updated to match Dockerfile
```

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Reusable Workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [uv Documentation](https://github.com/astral-sh/uv)
