"""MCP server implementation for ask-another."""

import os
import re
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("ask-another")

# Model registry: {model_id: api_key}
_model_registry: dict[str, str] = {}


def _parse_model_config(var_name: str, value: str) -> tuple[str, str]:
    """Parse a MODEL_* environment variable value.

    Expected format: provider/model-name;api-key

    Returns:
        Tuple of (model_id, api_key)

    Raises:
        ValueError: If format is invalid
    """
    if ";" not in value:
        raise ValueError(
            f"Invalid format for {var_name}: expected 'provider/model-name;api-key'"
        )

    parts = value.split(";", 1)
    model_id = parts[0].strip()
    api_key = parts[1].strip()

    if not model_id:
        raise ValueError(f"Invalid format for {var_name}: model identifier is empty")

    if "/" not in model_id:
        raise ValueError(
            f"Invalid format for {var_name}: model identifier must be 'provider/model-name'"
        )

    if not api_key:
        raise ValueError(f"Invalid format for {var_name}: API key is empty")

    return model_id, api_key


def _load_model_registry() -> None:
    """Scan environment for MODEL_* variables and populate registry."""
    global _model_registry
    _model_registry = {}

    model_var_pattern = re.compile(r"^MODEL_\w+$")

    for var_name, value in os.environ.items():
        if model_var_pattern.match(var_name):
            model_id, api_key = _parse_model_config(var_name, value)
            _model_registry[model_id] = api_key


# Load models on module import
_load_model_registry()


@mcp.tool()
def list_models() -> list[str]:
    """List all available model identifiers.

    Returns:
        Array of model identifiers in 'provider/model-name' format.
    """
    return list(_model_registry.keys())


@mcp.tool()
def completion(
    model: str,
    prompt: str,
    system: str | None = None,
    temperature: float = 1.0,
) -> str:
    """Get a completion from the specified LLM.

    Args:
        model: Model identifier in 'provider/model-name' format (e.g., 'openai/gpt-4o')
        prompt: The user prompt to send to the model
        system: Optional system prompt
        temperature: Sampling temperature (0.0-2.0, default 1.0)

    Returns:
        The model's text response
    """
    import litellm

    # Validate model is in allowlist
    if model not in _model_registry:
        raise ValueError(f"Model not allowed: {model}")

    # Validate temperature
    if not 0.0 <= temperature <= 2.0:
        raise ValueError("Temperature must be between 0.0 and 2.0")

    # Get API key for this model
    api_key = _model_registry[model]

    # Build messages
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # Make the completion request
    response = litellm.completion(
        model=model,
        messages=messages,
        temperature=temperature,
        api_key=api_key,
        timeout=60,
    )

    # Extract and return the response text
    return response.choices[0].message.content


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
