SHELL := /bin/bash
.PHONY: help test smoke integration mcpb verify validate bump-patch bump-minor bump-major install-hooks release clean

help:
	@echo "Targets:"
	@echo "  make test              Run unit tests (fast, no network)"
	@echo "  make smoke             Run MCP boot smoke tests (no provider keys needed)"
	@echo "  make integration       Run live integration tests (requires PROVIDER_* env vars)"
	@echo "  make verify            Check manifest.json and plugin.json versions match (fast)"
	@echo "  make validate          verify + npx mcpb validate manifest.json (opt-in pre-push check)"
	@echo "  make mcpb              Validate manifest and build ask-another.mcpb"
	@echo "  make bump-patch        Bump patch version in manifest.json + plugin.json"
	@echo "  make bump-minor        Bump minor version (zero patch)"
	@echo "  make bump-major        Bump major version (zero minor + patch)"
	@echo "  make install-hooks     Set core.hooksPath to .githooks (pre-commit runs make verify)"
	@echo "  make release VERSION=X.Y.Z"
	@echo "                         Verify clean tree + manifest/plugin versions match,"
	@echo "                         build .mcpb, tag vX.Y.Z, push, create GitHub release"
	@echo "  make clean             Remove built artifacts"

test:
	uv run pytest tests/ -q

smoke:
	uv run pytest tests/integration/test_mcp_smoke.py -m integration -v

integration:
	uv run pytest tests/integration -m integration -v

verify:
	@manifest_version=$$(python3 -c 'import json; print(json.load(open("manifest.json"))["version"])'); \
	  plugin_version=$$(python3 -c 'import json; print(json.load(open("plugins/ask-another/.claude-plugin/plugin.json"))["version"])'); \
	  if [ "$$manifest_version" != "$$plugin_version" ]; then \
	    echo "ERROR: manifest.json ($$manifest_version) != plugin.json ($$plugin_version)"; exit 1; \
	  fi; \
	  echo "OK: versions match at $$manifest_version"

validate: verify
	@npx -y @anthropic-ai/mcpb validate manifest.json
	@echo "OK: mcpb manifest valid"

define BUMP_SCRIPT
import re, sys
files = ["manifest.json", "plugins/ask-another/.claude-plugin/plugin.json"]
content = open(files[0]).read()
m = re.search(r'"version":\s*"(\d+)\.(\d+)\.(\d+)"', content)
major, minor, patch = map(int, m.groups())
old = f"{major}.{minor}.{patch}"
t = sys.argv[1]
if t == "patch": patch += 1
elif t == "minor": minor += 1; patch = 0
elif t == "major": major += 1; minor = 0; patch = 0
else: sys.exit(f"ERROR: unknown bump type {t}")
new = f"{major}.{minor}.{patch}"
for path in files:
    text = open(path).read()
    text = re.sub(r'"version":\s*"\d+\.\d+\.\d+"', f'"version": "{new}"', text, count=1)
    open(path, "w").write(text)
print(f"{old} -> {new}")
endef
export BUMP_SCRIPT

bump-patch:
	@python3 -c "$$BUMP_SCRIPT" patch

bump-minor:
	@python3 -c "$$BUMP_SCRIPT" minor

bump-major:
	@python3 -c "$$BUMP_SCRIPT" major

install-hooks:
	@git config core.hooksPath .githooks
	@echo "Hooks installed. .githooks/pre-commit will run 'make verify' before each commit."

mcpb:
	@npx -y @anthropic-ai/mcpb validate manifest.json
	@npx -y @anthropic-ai/mcpb pack . ask-another.mcpb
	@printf "\nBuilt: %s (%s bytes)\n" ask-another.mcpb "$$(stat -f%z ask-another.mcpb 2>/dev/null || stat -c%s ask-another.mcpb)"
	@printf "sha256: %s\n" "$$(shasum -a 256 ask-another.mcpb | cut -d' ' -f1)"

release: mcpb
	@if [ -z "$(VERSION)" ]; then echo "ERROR: VERSION required (e.g. make release VERSION=2.0.13)"; exit 1; fi
	@if [ -n "$$(git status --porcelain)" ]; then echo "ERROR: working tree is dirty — commit or stash first"; exit 1; fi
	@$(MAKE) -s verify
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
