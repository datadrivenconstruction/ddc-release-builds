#!/usr/bin/env python3
"""Check the licence content of the finished Linux/macOS assets (run on the downloaded draft release).

    verify_release_assets.py <folder-with-assets>

Exit code 1 and a list of problems when something required is missing.
"""
import re
import sys
import tarfile
from pathlib import Path

FORBIDDEN = re.compile(rb'/home/runner|/Users/runner|C:\Users\|hostedtoolcache')
VENDOR = re.compile(rb'ACadSharp|RealDWG|Teigha|Open Design Alliance', re.I)


def names(tf):
    return [m.name for m in tf.getmembers() if m.isfile()]


def main():
    root = Path(sys.argv[1])
    bad = []
    for arc in sorted(root.glob('*.tar.gz')):
        if arc.name.startswith('ddc-data-viewer'):
            continue
        with tarfile.open(arc) as tf:
            files = names(tf)
            short = [f.split('/', 1)[1] if '/' in f else f for f in files]
            def has(x):
                return any(s == x or s.startswith(x) for s in short)
            for need in ('LICENSE.txt', 'MANIFEST.json') if not arc.name.startswith('rvt') else ('LICENSE.txt', 'EULA.txt', 'NOTICE.txt', 'THIRD_PARTY_CRATES.txt', 'licenses/THIRD-PARTY-NOTICES.txt'):
                if not has(need):
                    bad.append('%s: missing %s' % (arc.name, need))
            if not arc.name.startswith('rvt'):
                if not has('licenses/README.txt'):
                    bad.append('%s: no licenses/ folder' % arc.name)
                if any(re.search(r'_hashlib|libcrypto', s) for s in short) and not has('licenses/Apache-2.0.txt'):
                    bad.append('%s: OpenSSL licence text missing' % arc.name)
                if any(re.search(r'_ctypes', s) for s in short) and not has('licenses/MIT-libffi.txt'):
                    bad.append('%s: libffi licence text missing' % arc.name)
                if any(re.search(r'_decimal', s) for s in short) and not has('licenses/BSD-2-mpdecimal.txt'):
                    bad.append('%s: mpdecimal licence text missing' % arc.name)
                if any(re.search(r'_sha2|_md5', s) for s in short) and not has('licenses/MIT-HACL.txt'):
                    bad.append('%s: HACL* licence text missing' % arc.name)
            for m in tf.getmembers():
                if not m.isfile() or m.size > 3_000_000:
                    continue
                data = tf.extractfile(m).read()
                if m.name.endswith(('.txt', '.json', 'NOTICE')) and (VENDOR.search(data) or FORBIDDEN.search(data)):
                    bad.append('%s: %s mentions a vendor or a build path' % (arc.name, m.name))
            lic = next((f for f in files if f.endswith('/LICENSE.txt')), None)
            if lic:
                text = tf.extractfile(lic).read().decode('utf-8', 'replace')
                if 'non-commercial' not in text.lower():
                    bad.append('%s: LICENSE.txt does not state non-commercial use' % arc.name)
            if arc.name.startswith('rvt'):
                notice = tf.extractfile(next(f for f in files if f.endswith('/NOTICE.txt'))).read().decode('utf-8', 'replace')
                if 'licensed under the Apache License, Version 2.0 (see LICENSE)' in notice:
                    bad.append('%s: NOTICE contradicts the EULA' % arc.name)
    for arch in ('x64', 'arm64'):
        for need in ('ddc-data-viewer-*-linux-%s.AppImage' % arch, 'ddc-data-viewer-*-linux-%s.deb' % arch,
                     'ddc-data-viewer-*-linux-%s-third-party-sources.tar.xz*' % arch, 'THIRD_PARTY_NOTICES-linux-%s.txt' % arch):
            if not list(root.glob(need)):
                bad.append('missing asset ' + need)
    for need in ('SOURCE-OFFER*.txt',):
        if not list(root.glob(need)):
            bad.append('missing asset ' + need)
    for arch in ('macos-arm64', 'macos-x64'):
        for need in ('ddc-data-viewer-*-%s.dmg' % arch, 'ddc-data-viewer-*-%s.app.tar.gz' % arch):
            if not list(root.glob(need)):
                bad.append('missing asset ' + need)
    for app in sorted(root.glob('ddc-data-viewer-*.app.tar.gz')):
        with tarfile.open(app) as tf:
            if not any(n.endswith('Contents/Resources/licenses/THIRD_PARTY_NOTICES.txt') for n in names(tf)):
                bad.append('%s: Contents/Resources/licenses/THIRD_PARTY_NOTICES.txt missing' % app.name)
    for b in bad:
        print('PROBLEM:', b)
    print('verified %s: %d problem(s)' % (root, len(bad)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
