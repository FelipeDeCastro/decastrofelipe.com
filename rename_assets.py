#!/usr/bin/env python3
"""
Rename asset files and folders to be human-readable.

Changes:
1. assets/6303bbde7e8891552c333a00/ → assets/img/
   (images, css, js subfolders)
2. assets/6022af993a6b2191db3ed10c/ → merged into assets/img/
3. Strip hex prefixes from image/media files:
   6303c42fe8b81fee32359e5c_Felipe de Castro.svg → Felipe de Castro.svg
4. CSS: decastrofelipe.webflow.shared.098991e7a.css → style.css
5. assets/css/ and assets/js/ stay (top-level, already clean structure)
6. JS files keep their hash names (cache-busting, internal references)
"""

import os
import re
import shutil
import glob
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, 'assets')

# Mapping of old paths → new paths (relative to ROOT)
renames = {}

def collect_renames():
    """Build the full rename map."""

    # --- 1. Main hash folder → assets/img/ ---
    old_main = os.path.join(ASSETS, '6303bbde7e8891552c333a00')
    new_main = os.path.join(ASSETS, 'img')

    if os.path.exists(old_main):
        for dirpath, dirnames, filenames in os.walk(old_main):
            for f in filenames:
                old_abs = os.path.join(dirpath, f)
                # Compute relative path within the hash folder
                rel = os.path.relpath(old_abs, old_main)
                subdir = os.path.dirname(rel)
                basename = os.path.basename(rel)

                if subdir in ('css', 'js'):
                    # CSS: simplify name
                    if subdir == 'css' and 'webflow.shared' in basename:
                        new_name = 'style.css'
                    else:
                        # JS: keep original names (hash-based for cache-busting)
                        new_name = basename
                    new_abs = os.path.join(new_main, subdir, new_name)
                else:
                    # Image/media files: strip hex prefix
                    new_name = strip_hex_prefix(basename)
                    new_abs = os.path.join(new_main, new_name)

                old_rel = os.path.relpath(old_abs, ROOT)
                new_rel = os.path.relpath(new_abs, ROOT)
                renames[old_rel] = new_rel

    # --- 2. Secondary hash folder → assets/img/ ---
    old_secondary = os.path.join(ASSETS, '6022af993a6b2191db3ed10c')
    if os.path.exists(old_secondary):
        for dirpath, dirnames, filenames in os.walk(old_secondary):
            for f in filenames:
                old_abs = os.path.join(dirpath, f)
                new_name = strip_hex_prefix(f)
                new_abs = os.path.join(new_main, new_name)

                old_rel = os.path.relpath(old_abs, ROOT)
                new_rel = os.path.relpath(new_abs, ROOT)
                renames[old_rel] = new_rel

    # --- 3. Top-level assets/css/ → simplify CSS name ---
    old_css_dir = os.path.join(ASSETS, 'css')
    if os.path.exists(old_css_dir):
        for f in os.listdir(old_css_dir):
            old_abs = os.path.join(old_css_dir, f)
            if os.path.isfile(old_abs) and 'webflow.shared' in f:
                new_abs = os.path.join(old_css_dir, 'style.css')
                old_rel = os.path.relpath(old_abs, ROOT)
                new_rel = os.path.relpath(new_abs, ROOT)
                renames[old_rel] = new_rel


def strip_hex_prefix(filename):
    """Remove Webflow hex prefix from filename.
    e.g. '6303c42fe8b81fee32359e5c_Felipe de Castro.svg' → 'Felipe de Castro.svg'
    """
    m = re.match(r'^[0-9a-f]{20,}_(.+)$', filename, re.IGNORECASE)
    if m:
        return m.group(1)
    return filename


def execute_renames():
    """Move files to their new locations."""
    print("\n[1/3] Renaming asset files...\n")

    for old_rel, new_rel in sorted(renames.items()):
        old_abs = os.path.join(ROOT, old_rel)
        new_abs = os.path.join(ROOT, new_rel)

        if not os.path.exists(old_abs):
            print(f"  ⚠ SKIP (not found): {old_rel}")
            continue

        # Create target directory
        os.makedirs(os.path.dirname(new_abs), exist_ok=True)

        # Move the file
        shutil.move(old_abs, new_abs)
        short_old = old_rel.replace('assets/', '')
        short_new = new_rel.replace('assets/', '')
        print(f"  ✓ {short_old}")
        print(f"    → {short_new}")

    # Clean up empty hash folders
    for folder in ['6303bbde7e8891552c333a00', '6022af993a6b2191db3ed10c']:
        path = os.path.join(ASSETS, folder)
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"\n  ✓ Removed empty folder: assets/{folder}/")


def update_html_references():
    """Update all references in HTML files."""
    print("\n[2/3] Updating references in HTML files...\n")

    html_files = glob.glob(os.path.join(ROOT, '*.html'))

    # Build replacement pairs (old URL path → new URL path)
    # Need to handle both URL-encoded and non-encoded versions
    replacements = []
    for old_rel, new_rel in renames.items():
        # The HTML may have URL-encoded paths (spaces → %20)
        old_encoded = urllib.parse.quote(old_rel, safe='/')
        new_encoded = urllib.parse.quote(new_rel, safe='/')
        replacements.append((old_encoded, new_encoded))

        # Also handle non-encoded version (some attributes use raw paths)
        if old_rel != old_encoded:
            replacements.append((old_rel, new_rel))

    # Sort by length (longest first) to avoid partial replacements
    replacements.sort(key=lambda x: len(x[0]), reverse=True)

    for html_file in sorted(html_files):
        name = os.path.basename(html_file)
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        for old_path, new_path in replacements:
            content = content.replace(old_path, new_path)

        if content != original:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(content)
            count = sum(1 for old, _ in replacements if old in original)
            print(f"  ✓ {name}")
        else:
            print(f"  - {name} (no changes)")


def update_css_references():
    """Update references inside CSS files (e.g. url() for fonts or images)."""
    print("\n[3/3] Updating references in CSS files...\n")

    css_files = glob.glob(os.path.join(ROOT, 'assets', '**', '*.css'), recursive=True)

    replacements = []
    for old_rel, new_rel in renames.items():
        old_encoded = urllib.parse.quote(old_rel, safe='/')
        new_encoded = urllib.parse.quote(new_rel, safe='/')
        replacements.append((old_encoded, new_encoded))
        if old_rel != old_encoded:
            replacements.append((old_rel, new_rel))

    replacements.sort(key=lambda x: len(x[0]), reverse=True)

    for css_file in sorted(css_files):
        rel_name = os.path.relpath(css_file, ROOT)
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        for old_path, new_path in replacements:
            content = content.replace(old_path, new_path)

        if content != original:
            with open(css_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ {rel_name}")
        else:
            print(f"  - {rel_name} (no changes)")


def main():
    print("=" * 60)
    print("  Renaming assets to human-readable names")
    print("=" * 60)

    collect_renames()
    print(f"\n  Found {len(renames)} files to rename")

    execute_renames()
    update_html_references()
    update_css_references()

    print("\n" + "=" * 60)
    print("  Done! Asset files are now human-readable.")
    print("=" * 60)


if __name__ == '__main__':
    main()
