"""Interactive and scriptable command-line interface."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .services import LookupError, ip_lookup, my_ip, phone_lookup, username_lookup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GhostTrack — public IP, phone metadata, and username links"
    )
    parser.add_argument("--version", action="version", version=f"GhostTrack {__version__}")
    parser.add_argument("--json", action="store_true", dest="json_output",
                        help="Emit machine-readable JSON with a subcommand")
    sub = parser.add_subparsers(dest="command")

    ip_cmd = sub.add_parser("ip", help="Approximate public IP geolocation")
    ip_cmd.add_argument("address")
    own_cmd = sub.add_parser("my-ip", help="Show the public IP of this connection")
    phone_cmd = sub.add_parser("phone", help="Phone number numbering-plan metadata")
    phone_cmd.add_argument("number")
    phone_cmd.add_argument("--region", default="ID",
                           help="ISO 3166-1 alpha-2 default region (default: ID)")
    name_cmd = sub.add_parser("username", help="Public profile links / limited API checks")
    name_cmd.add_argument("handle")
    name_cmd.add_argument("--no-check", action="store_true",
                          help="Generate links without querying verification APIs")
    for command in (ip_cmd, own_cmd, phone_cmd, name_cmd):
        command.add_argument("--json", action="store_true", dest="json_output",
                             default=argparse.SUPPRESS)
    return parser


def run(command: str, argument: str = "", *, region: str = "ID",
        check: bool = True) -> dict:
    if command == "ip":
        return ip_lookup(argument)
    if command == "my-ip":
        return my_ip()
    if command == "phone":
        return phone_lookup(argument, region=region)
    if command == "username":
        return username_lookup(argument, check=check)
    raise LookupError("Unknown command")


def show(data: dict, *, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    if "profiles" in data:
        print(f"\nProfile links for @{data['username']}:\n")
        for profile in data["profiles"]:
            label = profile["status"].replace("_", " ").upper()
            print(f"  {profile['platform']:<13} [{label:<10}] {profile['url']}")
        print("\n" + data["note"])
    else:
        print()
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"  {key.replace('_', ' ').title()}:")
                for subkey, subvalue in value.items():
                    print(f"    {subkey.replace('_', ' ').title():<20} {subvalue if subvalue is not None else 'N/A'}")
            else:
                if isinstance(value, list):
                    value = ", ".join(str(x) for x in value)
                print(f"  {key.replace('_', ' ').title():<24} {value if value is not None else 'N/A'}")


def interactive() -> int:
    menu = (
        "\nGhostTrack — OSINT utilities\n"
        "  [1] IP Tracker\n"
        "  [2] Show Your IP\n"
        "  [3] Phone Number Tracker\n"
        "  [4] Username Tracker\n"
        "  [0] Exit\n"
    )
    while True:
        print(menu)
        try:
            choice = input("Select option: ").strip()
            if choice == "0":
                return 0
            if choice == "1":
                data = run("ip", input("Public IP address: "))
            elif choice == "2":
                data = run("my-ip")
            elif choice == "3":
                number = input("Phone number (prefer +international format): ")
                region = input("Region for local numbers [ID]: ").strip() or "ID"
                data = run("phone", number, region=region)
            elif choice == "4":
                data = run("username", input("Username: "))
            else:
                print("Choose 0, 1, 2, 3, or 4.")
                continue
            show(data)
            input("\nPress Enter to continue...")
        except LookupError as exc:
            print(f"\nLookup error: {exc}", file=sys.stderr)
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\nInterrupted.")
            return 130


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command is None:
        return interactive()
    try:
        data = run(args.command, getattr(args, "address", "")
                   or getattr(args, "number", "")
                   or getattr(args, "handle", ""),
                   region=getattr(args, "region", "ID"),
                   check=not getattr(args, "no_check", False))
    except LookupError as exc:
        if args.json_output:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Lookup error: {exc}", file=sys.stderr)
        return 1
    show(data, as_json=args.json_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
