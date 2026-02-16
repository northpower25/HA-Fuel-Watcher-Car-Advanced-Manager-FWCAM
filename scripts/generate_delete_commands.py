#!/usr/bin/env python3
"""
Script to generate commands for deleting all pre-releases before v0.1.0
This script generates the GitHub CLI commands that need to be run.
"""

REPO_OWNER = "northpower25"
REPO_NAME = "HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM"

# All pre-releases to delete (v0.0.82 to v0.0.110)
PRERELEASES = [
    ("v0.0.110", "286609357"),
    ("v0.0.109", "286596521"),
    ("v0.0.108", "286593561"),
    ("v0.0.107", "286584664"),
    ("v0.0.106", "286579575"),
    ("v0.0.105", "286573540"),
    ("v0.0.104", "286568023"),
    ("v0.0.103", "286565209"),
    ("v0.0.102", "286549245"),
    ("v0.0.101", "286545944"),
    ("v0.0.100", "286542677"),
    ("v0.0.99", "286540307"),
    ("v0.0.98", "286536662"),
    ("v0.0.97", "286532453"),
    ("v0.0.96", "286532099"),
    ("v0.0.95", "286529267"),
    ("v0.0.94", "286526860"),
    ("v0.0.93", "286521817"),
    ("v0.0.92", "286518202"),
    ("v0.0.91", "286512585"),
    ("v0.0.90", "286509900"),
    ("v0.0.89", "286505528"),
    ("v0.0.88", "286502750"),
    ("v0.0.87", "286439846"),
    ("v0.0.86", "286428784"),
    ("v0.0.85", "286416742"),
    ("v0.0.84", "286413507"),
    ("v0.0.83", "286410011"),
    ("v0.0.82", "286406417"),
]

def main():
    print("=" * 80)
    print("DELETE PRE-RELEASES SCRIPT")
    print("=" * 80)
    print(f"\nTotal pre-releases to delete: {len(PRERELEASES)}")
    print(f"Repository: {REPO_OWNER}/{REPO_NAME}")
    print("\n" + "=" * 80)
    print("OPTION 1: Delete all at once (copy and paste)")
    print("=" * 80)
    print("\n#!/bin/bash")
    print("# Delete all pre-releases before v0.1.0\n")
    
    for tag, release_id in PRERELEASES:
        print(f'gh release delete {tag} --repo {REPO_OWNER}/{REPO_NAME} --yes  # ID: {release_id}')
    
    print("\n" + "=" * 80)
    print("OPTION 2: Single command with loop")
    print("=" * 80)
    print("\n#!/bin/bash")
    print("# Delete all pre-releases using a loop\n")
    
    tags = " ".join([tag for tag, _ in PRERELEASES])
    print(f'for tag in {tags}; do')
    print(f'  gh release delete "$tag" --repo {REPO_OWNER}/{REPO_NAME} --yes')
    print(f'done')
    
    print("\n" + "=" * 80)
    print("OPTION 3: Using GitHub API (with curl)")
    print("=" * 80)
    print("\n# Set your GitHub token")
    print("# export GITHUB_TOKEN='your_token_here'\n")
    
    for tag, release_id in PRERELEASES:
        print(f'curl -X DELETE -H "Authorization: token $GITHUB_TOKEN" \\')
        print(f'  https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/{release_id}')
    
    print("\n" + "=" * 80)
    print("\nTo use these commands:")
    print("1. Make sure you're authenticated with GitHub CLI: gh auth login")
    print("2. Copy one of the options above")
    print("3. Paste and run in your terminal")
    print("=" * 80)

if __name__ == "__main__":
    main()
