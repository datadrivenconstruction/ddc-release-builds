#!/usr/bin/env python3
"""Licence files for a Nuitka standalone folder (called by the products' build_cli.py through DDC_LICENSE_HOOK).

    python_licenses.py <dist-folder>

Writes <dist-folder>/licenses/: the licence texts of the components compiled into or bundled with the
CPython runtime (OpenSSL, libffi, expat, mpdecimal, HACL*) and, on Debian/Ubuntu, the copyright file of the
distribution package of every bundled shared library plus the GPL/LGPL texts when a package needs them.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEXTS = HERE.parent / 'legal' / 'licenses'
BY_FILE = [  # (file name pattern, texts to ship)
    (r'^(_hashlib|_ssl)\b|libcrypto|libssl', ['Apache-2.0.txt', 'OpenSSL-NOTICE.txt']),
    (r'^_ctypes\b|libffi', ['MIT-libffi.txt']),
    (r'^(pyexpat|_elementtree)\b|libexpat', ['MIT-expat.txt']),
    (r'^_decimal\b|libmpdec', ['BSD-2-mpdecimal.txt']),
    (r'^(_md5|_sha1|_sha2|_sha3|_blake2)\b', ['MIT-HACL.txt']),
]


def is_native(p):
    return re.search(r'\.(so(\.\d+)*|dylib|pyd)$', p.name) is not None


def out(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def main():
    dist = Path(sys.argv[1])
    lic = dist / 'licenses'
    lic.mkdir(exist_ok=True)
    natives = sorted(p for p in dist.rglob('*') if p.is_file() and is_native(p))
    texts = set()
    for p in natives:
        for pattern, names in BY_FILE:
            if re.search(pattern, p.name):
                texts.update(names)
    for name in sorted(texts):
        shutil.copyfile(TEXTS / name, lic / name)
    lines = ['Components bundled with the CPython runtime and their licence files (this folder):']
    lines += ['  ' + n for n in sorted(texts)]
    if sys.platform.startswith('linux') and shutil.which('dpkg'):
        pkgs = {}
        for p in natives:
            if not re.match(r'^lib.*\.so(\.\d+)+$', p.name):
                continue  # extension modules of the interpreter are not distribution packages
            hit = out(['dpkg', '-S', '*/' + p.name]).splitlines()
            for line in hit:
                if ': ' in line:
                    for pkg in line.split(': ', 1)[0].split(', '):
                        pkgs.setdefault(pkg.split(':')[0], []).append(p.name)
                    break
        lines += ['', 'Distribution packages the shared libraries were taken from (copyright files in this folder):']
        needs_common = set()
        for pkg, files in sorted(pkgs.items()):
            ver = out(['dpkg-query', '-W', '-f=${Version}', pkg])
            cp = Path('/usr/share/doc') / pkg / 'copyright'
            if cp.exists():
                shutil.copyfile(cp, lic / ('copyright-%s.txt' % pkg))
                body = cp.read_text(encoding='utf-8', errors='replace')
                for key in ('GPL-3', 'GPL-2', 'LGPL-2.1', 'LGPL-3', 'LGPL-2', 'MPL-2.0', 'Apache-2.0', 'BSD'):
                    if key in body:
                        needs_common.add(key)
            lines.append('  %s %s: %s' % (pkg, ver, ', '.join(sorted(set(files)))))
        common = Path('/usr/share/common-licenses')
        for key in sorted(needs_common):
            f = common / key
            if f.is_file():
                shutil.copyfile(f, lic / ('common-' + key + '.txt'))
        lines.append('')
        lines.append('The libraries are used unchanged; the licence of each is given in its copyright file.')
    (lic / 'README.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('licence files:', len(list(lic.iterdir())))


if __name__ == '__main__':
    main()
