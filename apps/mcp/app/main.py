from .server import create_mcp


def main() -> None:
    mcp = create_mcp()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

