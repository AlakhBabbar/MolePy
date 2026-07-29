import os
import typer
from pathlib import Path
from typing_extensions import Annotated
from molepy import agent

# Initialize Typer app
app = typer.Typer(
    help="Molepy: An autonomous AI coding agent that explores and modifies codebases.",
    add_completion=False,
)

@app.command()
def main(
    request: Annotated[str, typer.Argument(help="The product request or feature description.")],
    repo: Annotated[Path, typer.Option(
        "--repo", 
        "-r", 
        help="Path to the repository directory. Defaults to current directory."
    )] = Path.cwd()
):
    """
    Run the molepy agent on a repository to fulfill a product request.
    """
    # 1. Fail fast if no API key is set
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        typer.secho(
            "❌ Error: API key missing! Please set the GROQ_API_KEY environment variable.", 
            fg=typer.colors.RED
        )
        typer.secho("Example: export GROQ_API_KEY='your-key-here'", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    # 2. Validate the repository path
    repo_path = repo.resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        typer.secho(f"❌ Error: The directory '{repo_path}' does not exist.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # 3. Start the agent loop
    try:
        agent.run_agent(product_request=request, repo_path=str(repo_path))
    except Exception as e:
        typer.secho(f"\n❌ Agent execution failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()