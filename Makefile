SHELL := /bin/bash
.PHONY: help test smoke integration dxt release clean

help:
	@echo "Targets:"
	@echo "  make test         Run unit tests (fast, no network)"
	@echo "  make smoke        Run MCP boot smoke tests (no provider keys needed)"
	@echo "  make integration  Run live integration tests (requires PROVIDER_* env vars)"
	@echo "  make dxt          Validate manifest and build ask-another.mcpb"
	@echo "  make release VERSION=X.Y.Z"
	@echo "                    Verify clean tree + manifest version match,"
	@echo "                    build .mcpb, tag vX.Y.Z, push, create GitHub release"
	@echo "  make clean        Remove built artifacts"

test:
	uv run pytest tests/ -q

smoke:
	uv run pytest tests/integration/test_mcp_smoke.py -m integration -v

integration:
	uv run pytest tests/integration -m integration -v

dxt:
	@npx -y @anthropic-ai/mcpb validate manifest.json
	@npx -y @anthropic-ai/mcpb pack . ask-another.mcpb
	@printf "\nBuilt: %s (%s bytes)\n" ask-another.mcpb "$$(stat -f%z ask-another.mcpb 2>/dev/null || stat -c%s ask-another.mcpb)"
	@printf "sha256: %s\n" "$$(shasum -a 256 ask-another.mcpb | cut -d' ' -f1)"

release: dxt
	@if [ -z "$(VERSION)" ]; then echo "ERROR: VERSION required (e.g. make release VERSION=2.0.9)"; exit 1; fi
	@if [ -n "$$(git status --porcelain)" ]; then echo "ERROR: working tree is dirty — commit or stash first"; exit 1; fi
	@manifest_version=$$(python3 -c 'import json; print(json.load(open("manifest.json"))["version"])'); \
	  if [ "$$manifest_version" != "$(VERSION)" ]; then \
	    echo "ERROR: manifest.json version ($$manifest_version) does not match VERSION=$(VERSION)"; exit 1; \
	  fi
	@if git rev-parse "v$(VERSION)" >/dev/null 2>&1; then echo "ERROR: tag v$(VERSION) already exists"; exit 1; fi
	git tag -a "v$(VERSION)" -m "Release v$(VERSION)"
	git push origin "v$(VERSION)"
	gh release create "v$(VERSION)" ./ask-another.mcpb --title "v$(VERSION)" --generate-notes
	@echo "Released v$(VERSION). Bundle attached to GitHub release."

clean:
	rm -f ask-another.mcpb
